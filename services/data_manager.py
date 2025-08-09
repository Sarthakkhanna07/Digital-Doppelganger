"""
Data Management Service for Time Capsule AI
Handles all database operations and data persistence
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json

from models import (
    ReminderData, TimelineEntry, TimeCapsule, EmotionProfile, 
    ActivityContext, CompletionStatus, SearchResult
)
from utils.database import DatabaseManager

class DataManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def store_reminder(self, reminder: ReminderData) -> str:
        """Store a reminder with all contextual data"""
        try:
            await self.db.execute_update(
                """INSERT INTO reminders 
                   (id, user_id, content, created_at, due_at, emotional_context, 
                    activity_context, location_context, delivery_count, status, user_response_history)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    reminder.id,
                    reminder.user_id,
                    reminder.content,
                    reminder.created_at,
                    reminder.due_at,
                    self.db.serialize_json(reminder.emotional_context.__dict__),
                    self.db.serialize_json(reminder.activity_context.__dict__),
                    self.db.serialize_json(reminder.location_context),
                    reminder.delivery_count,
                    reminder.completion_status.value,
                    self.db.serialize_json([r.__dict__ for r in reminder.user_response_history])
                )
            )
            
            # Also add to timeline
            await self.store_timeline_entry(TimelineEntry(
                id=f"timeline_{reminder.id}",
                user_id=reminder.user_id,
                timestamp=reminder.created_at,
                entry_type="reminder_created",
                content=f"Created reminder: {reminder.content}",
                emotional_state=reminder.emotional_context,
                context={"reminder_id": reminder.id, "due_at": reminder.due_at.isoformat()},
                related_entries=[],
                searchable_text=f"{reminder.content} reminder {reminder.emotional_context.primary_emotion}",
                tags=["reminder", reminder.emotional_context.primary_emotion, reminder.activity_context.primary_activity]
            ))
            
            return reminder.id
            
        except Exception as e:
            raise Exception(f"Failed to store reminder: {str(e)}")
    
    async def get_due_reminders(self, user_id: str, current_time: datetime) -> List[ReminderData]:
        """Get all reminders that are due for a user"""
        try:
            results = await self.db.execute_query(
                """SELECT * FROM reminders 
                   WHERE user_id = ? AND due_at <= ? AND status = 'pending'
                   ORDER BY due_at ASC""",
                (user_id, current_time)
            )
            
            reminders = []
            for row in results:
                reminder = self._row_to_reminder(row)
                reminders.append(reminder)
            
            return reminders
            
        except Exception as e:
            raise Exception(f"Failed to get due reminders: {str(e)}")
    
    async def update_reminder_delivery(self, reminder_id: str) -> None:
        """Update reminder delivery count and timestamp"""
        try:
            await self.db.execute_update(
                """UPDATE reminders 
                   SET delivery_count = delivery_count + 1
                   WHERE id = ?""",
                (reminder_id,)
            )
        except Exception as e:
            raise Exception(f"Failed to update reminder delivery: {str(e)}")
    
    async def store_timeline_entry(self, entry: TimelineEntry) -> str:
        """Store a timeline entry"""
        try:
            await self.db.execute_update(
                """INSERT INTO timeline_entries 
                   (id, user_id, timestamp, entry_type, content, emotional_state, 
                    context_data, searchable_text, tags, related_entries)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.id,
                    entry.user_id,
                    entry.timestamp,
                    entry.entry_type,
                    entry.content,
                    self.db.serialize_json(entry.emotional_state.__dict__),
                    self.db.serialize_json(entry.context),
                    entry.searchable_text,
                    self.db.serialize_json(entry.tags),
                    self.db.serialize_json(entry.related_entries)
                )
            )
            
            # Add to full-text search index
            await self.db.execute_update(
                """INSERT INTO timeline_fts (entry_id, content, searchable_text, tags)
                   VALUES (?, ?, ?, ?)""",
                (entry.id, entry.content, entry.searchable_text, ' '.join(entry.tags))
            )
            
            return entry.id
            
        except Exception as e:
            raise Exception(f"Failed to store timeline entry: {str(e)}")
    
    async def search_timeline(self, user_id: str, query: str, limit: int = 10) -> List[SearchResult]:
        """Search user's timeline using full-text search"""
        try:
            # Use FTS for text search
            results = await self.db.execute_query(
                """SELECT te.*, ts.rank 
                   FROM timeline_entries te
                   JOIN (
                       SELECT entry_id, rank
                       FROM timeline_fts 
                       WHERE timeline_fts MATCH ?
                       ORDER BY rank
                       LIMIT ?
                   ) ts ON te.id = ts.entry_id
                   WHERE te.user_id = ?
                   ORDER BY ts.rank DESC, te.timestamp DESC""",
                (query, limit, user_id)
            )
            
            search_results = []
            for row in results:
                # Reconstruct emotion profile
                emotional_state = self._deserialize_emotion_profile(row.get('emotional_state'))
                
                search_result = SearchResult(
                    entry_id=row['id'],
                    relevance_score=row.get('rank', 0.5),
                    content_snippet=row['content'][:200] + "..." if len(row['content']) > 200 else row['content'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    entry_type=row['entry_type'],
                    emotional_context=emotional_state
                )
                search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            raise Exception(f"Failed to search timeline: {str(e)}")
    
    async def get_user_timeline(self, user_id: str, days_back: int = 30) -> List[TimelineEntry]:
        """Get user's timeline for the specified number of days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            results = await self.db.execute_query(
                """SELECT * FROM timeline_entries 
                   WHERE user_id = ? AND timestamp >= ?
                   ORDER BY timestamp DESC""",
                (user_id, cutoff_date)
            )
            
            timeline = []
            for row in results:
                entry = self._row_to_timeline_entry(row)
                timeline.append(entry)
            
            return timeline
            
        except Exception as e:
            raise Exception(f"Failed to get user timeline: {str(e)}")
    
    async def store_time_capsule(self, capsule: TimeCapsule) -> str:
        """Store a time capsule for future delivery"""
        try:
            await self.db.execute_update(
                """INSERT INTO time_capsules 
                   (id, user_id, content, created_at, earliest_delivery, latest_delivery,
                    emotional_snapshot, context_snapshot)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    capsule.id,
                    capsule.user_id,
                    capsule.content,
                    capsule.created_at,
                    capsule.earliest_delivery,
                    capsule.latest_delivery,
                    self.db.serialize_json(capsule.emotional_snapshot.__dict__),
                    self.db.serialize_json(capsule.context_snapshot)
                )
            )
            
            return capsule.id
            
        except Exception as e:
            raise Exception(f"Failed to store time capsule: {str(e)}")
    
    async def get_due_time_capsules(self, user_id: str, current_time: datetime) -> List[TimeCapsule]:
        """Get time capsules ready for delivery"""
        try:
            results = await self.db.execute_query(
                """SELECT * FROM time_capsules 
                   WHERE user_id = ? AND earliest_delivery <= ? AND latest_delivery >= ?
                   AND delivered_at IS NULL
                   ORDER BY created_at ASC""",
                (user_id, current_time, current_time)
            )
            
            capsules = []
            for row in results:
                capsule = self._row_to_time_capsule(row)
                capsules.append(capsule)
            
            return capsules
            
        except Exception as e:
            raise Exception(f"Failed to get due time capsules: {str(e)}")
    
    async def mark_time_capsule_delivered(self, capsule_id: str) -> None:
        """Mark a time capsule as delivered"""
        try:
            await self.db.execute_update(
                "UPDATE time_capsules SET delivered_at = ? WHERE id = ?",
                (datetime.now(), capsule_id)
            )
        except Exception as e:
            raise Exception(f"Failed to mark time capsule as delivered: {str(e)}")
    
    def _row_to_reminder(self, row: Dict[str, Any]) -> ReminderData:
        """Convert database row to ReminderData object"""
        emotional_context = self._deserialize_emotion_profile(row.get('emotional_context'))
        activity_context = self._deserialize_activity_context(row.get('activity_context'))
        
        return ReminderData(
            id=row['id'],
            user_id=row['user_id'],
            content=row['content'],
            created_at=datetime.fromisoformat(row['created_at']),
            due_at=datetime.fromisoformat(row['due_at']),
            emotional_context=emotional_context,
            activity_context=activity_context,
            location_context=self.db.deserialize_json(row.get('location_context')),
            completion_status=CompletionStatus(row['status']),
            delivery_count=row['delivery_count'],
            user_response_history=[]  # TODO: Deserialize user responses
        )
    
    def _row_to_timeline_entry(self, row: Dict[str, Any]) -> TimelineEntry:
        """Convert database row to TimelineEntry object"""
        emotional_state = self._deserialize_emotion_profile(row.get('emotional_state'))
        
        return TimelineEntry(
            id=row['id'],
            user_id=row['user_id'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            entry_type=row['entry_type'],
            content=row['content'],
            emotional_state=emotional_state,
            context=self.db.deserialize_json(row.get('context_data', '{}')),
            related_entries=self.db.deserialize_json(row.get('related_entries', '[]')),
            searchable_text=row['searchable_text'],
            tags=self.db.deserialize_json(row.get('tags', '[]'))
        )
    
    def _row_to_time_capsule(self, row: Dict[str, Any]) -> TimeCapsule:
        """Convert database row to TimeCapsule object"""
        emotional_snapshot = self._deserialize_emotion_profile(row.get('emotional_snapshot'))
        
        return TimeCapsule(
            id=row['id'],
            user_id=row['user_id'],
            content=row['content'],
            created_at=datetime.fromisoformat(row['created_at']),
            earliest_delivery=datetime.fromisoformat(row['earliest_delivery']),
            latest_delivery=datetime.fromisoformat(row['latest_delivery']),
            delivered_at=datetime.fromisoformat(row['delivered_at']) if row.get('delivered_at') else None,
            emotional_snapshot=emotional_snapshot,
            context_snapshot=self.db.deserialize_json(row.get('context_snapshot', '{}'))
        )
    
    def _deserialize_emotion_profile(self, json_str: str) -> EmotionProfile:
        """Deserialize EmotionProfile from JSON"""
        if not json_str:
            return EmotionProfile(
                primary_emotion="neutral",
                intensity=0.5,
                secondary_emotions={},
                confidence_score=0.3,
                detected_indicators=[],
                contextual_factors={}
            )
        
        try:
            data = json.loads(json_str)
            return EmotionProfile(
                primary_emotion=data.get('primary_emotion', 'neutral'),
                intensity=data.get('intensity', 0.5),
                secondary_emotions=data.get('secondary_emotions', {}),
                confidence_score=data.get('confidence_score', 0.3),
                detected_indicators=data.get('detected_indicators', []),
                contextual_factors=data.get('contextual_factors', {})
            )
        except (json.JSONDecodeError, KeyError):
            return EmotionProfile(
                primary_emotion="neutral",
                intensity=0.5,
                secondary_emotions={},
                confidence_score=0.3,
                detected_indicators=[],
                contextual_factors={}
            )
    
    def _deserialize_activity_context(self, json_str: str) -> ActivityContext:
        """Deserialize ActivityContext from JSON"""
        if not json_str:
            return ActivityContext(
                primary_activity="general",
                location_type="unknown",
                social_context="alone",
                time_context="general",
                energy_level="medium",
                detected_keywords=[]
            )
        
        try:
            data = json.loads(json_str)
            return ActivityContext(
                primary_activity=data.get('primary_activity', 'general'),
                location_type=data.get('location_type', 'unknown'),
                social_context=data.get('social_context', 'alone'),
                time_context=data.get('time_context', 'general'),
                energy_level=data.get('energy_level', 'medium'),
                detected_keywords=data.get('detected_keywords', [])
            )
        except (json.JSONDecodeError, KeyError):
            return ActivityContext(
                primary_activity="general",
                location_type="unknown",
                social_context="alone",
                time_context="general",
                energy_level="medium",
                detected_keywords=[]
            )