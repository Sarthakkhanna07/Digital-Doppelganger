"""
Active Nudging System for Time Capsule AI
Proactively engages users to capture meaningful life moments
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from models import TimelineEntry, EmotionProfile, ActivityContext
from utils.database import DatabaseManager

class NudgeManager:
    def __init__(self, data_manager, tone_manager, emotion_analyzer):
        self.data_manager = data_manager
        self.tone_manager = tone_manager
        self.emotion_analyzer = emotion_analyzer
        self.db = data_manager.db
        
        # Nudge templates for different contexts
        self.nudge_templates = {
            'general': [
                "Hey, what are you doing right now? Want me to save this moment for later?",
                "Quick check-in - how are you feeling and what's happening in your world?",
                "Capturing life moments... what's going on with you right now?",
                "Time for a life snapshot! What are you up to and how are you feeling?"
            ],
            'morning': [
                "Good morning! How are you starting your day? Want me to remember this moment?",
                "Morning vibes check! What's your energy like and what are you doing?",
                "New day, new moments to capture! How are you feeling this morning?"
            ],
            'evening': [
                "How did your day go? Want me to capture how you're feeling right now?",
                "Evening reflection time - what's on your mind and how are you feeling?",
                "Winding down? Tell me about your current mood and what you're doing."
            ],
            'achievement': [
                "I sense you might have accomplished something! Want to capture this feeling?",
                "Feeling proud about something? Let me save this moment for you!",
                "Achievement vibes detected! What did you just accomplish?"
            ],
            'stress_relief': [
                "Taking a breather? How are you feeling now compared to earlier?",
                "Stress levels check - are you feeling better? Want me to remember this?",
                "Moment of calm? Let me capture how you're feeling right now."
            ]
        }
        
        # Optimal nudge timing patterns (hours of day)
        self.optimal_times = {
            'morning_person': [7, 8, 9, 19, 20],
            'night_owl': [10, 11, 22, 23],
            'regular_schedule': [9, 13, 17, 21],
            'flexible': [8, 12, 16, 20]
        }
        
        # Context-based nudge triggers
        self.context_triggers = {
            'post_workout': {
                'keywords': ['workout', 'gym', 'exercise', 'run', 'fitness'],
                'delay_minutes': 15,  # Nudge 15 minutes after workout mention
                'template_category': 'achievement'
            },
            'work_completion': {
                'keywords': ['finished', 'completed', 'done with', 'submitted'],
                'delay_minutes': 10,
                'template_category': 'achievement'
            },
            'stress_mention': {
                'keywords': ['stressed', 'overwhelmed', 'pressure', 'deadline'],
                'delay_minutes': 60,  # Check in an hour later
                'template_category': 'stress_relief'
            },
            'social_activity': {
                'keywords': ['friends', 'family', 'dinner', 'party', 'hanging out'],
                'delay_minutes': 30,
                'template_category': 'general'
            }
        }
    
    async def schedule_daily_nudges(self, user_id: str) -> List[datetime]:
        """Schedule optimal nudge times for a user based on their patterns"""
        try:
            # Get user's activity patterns
            user_pattern = await self._analyze_user_activity_pattern(user_id)
            
            # Determine user type
            user_type = self._classify_user_schedule_type(user_pattern)
            
            # Get optimal times for this user type
            optimal_hours = self.optimal_times.get(user_type, self.optimal_times['regular_schedule'])
            
            # Schedule 1-2 nudges per day
            num_nudges = random.choice([1, 2])
            selected_hours = random.sample(optimal_hours, min(num_nudges, len(optimal_hours)))
            
            # Create datetime objects for today
            today = datetime.now().date()
            scheduled_times = []
            
            for hour in selected_hours:
                # Add some randomness to the exact minute
                minute = random.randint(0, 59)
                nudge_time = datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute))
                
                # If the time has already passed today, schedule for tomorrow
                if nudge_time <= datetime.now():
                    nudge_time += timedelta(days=1)
                
                scheduled_times.append(nudge_time)
            
            # Store scheduled nudges in database
            await self._store_scheduled_nudges(user_id, scheduled_times)
            
            return scheduled_times
            
        except Exception as e:
            # Fallback to default schedule
            default_time = datetime.now() + timedelta(hours=4)
            await self._store_scheduled_nudges(user_id, [default_time])
            return [default_time]
    
    async def generate_nudge_message(self, user_id: str, context: Dict[str, Any] = None) -> str:
        """Generate a personalized nudge message"""
        try:
            if context is None:
                context = {}
            
            # Get user's tone profile
            tone_profile = await self.tone_manager.build_user_profile(user_id)
            
            # Determine nudge category based on context
            nudge_category = self._determine_nudge_category(context)
            
            # Select template
            templates = self.nudge_templates.get(nudge_category, self.nudge_templates['general'])
            base_message = random.choice(templates)
            
            # Adapt tone
            adapted_message = await self.tone_manager.adapt_response_tone(
                base_message, 
                tone_profile,
                context
            )
            
            return adapted_message
            
        except Exception as e:
            # Fallback to simple nudge
            return "Hey, what are you doing right now? Want me to save this moment for later?"
    
    async def process_nudge_response(self, user_id: str, response: str, nudge_context: Dict[str, Any]) -> str:
        """Process user's response to a nudge and create timeline entry"""
        try:
            # Analyze the response
            emotion_profile = await self.emotion_analyzer.analyze_emotion(response, {
                "time_of_day": datetime.now().strftime("%H:%M"),
                "day_of_week": datetime.now().strftime("%A"),
                "nudge_context": nudge_context
            })
            
            # Extract activity context from response
            from .nlp_engine import NLPEngine
            nlp = NLPEngine()
            activity_context = await nlp.detect_activity_context(response)
            
            # Create timeline entry
            timeline_entry = TimelineEntry(
                id=f"nudge_response_{datetime.now().timestamp()}",
                user_id=user_id,
                timestamp=datetime.now(),
                entry_type="nudge_response",
                content=response,
                emotional_state=emotion_profile,
                context={
                    "nudge_triggered": True,
                    "activity_context": activity_context.__dict__,
                    "nudge_context": nudge_context
                },
                related_entries=[],
                searchable_text=f"nudge response {response} {emotion_profile.primary_emotion} {activity_context.primary_activity}",
                tags=["nudge_response", emotion_profile.primary_emotion, activity_context.primary_activity]
            )
            
            # Store timeline entry
            await self.data_manager.store_timeline_entry(timeline_entry)
            
            # Generate follow-up response
            follow_up = await self._generate_nudge_follow_up(user_id, response, emotion_profile, activity_context)
            
            # Learn from this interaction for better future nudging
            await self._learn_from_nudge_interaction(user_id, response, emotion_profile, nudge_context)
            
            return follow_up
            
        except Exception as e:
            return "Thanks for sharing! I've captured this moment in your timeline. ✨"
    
    async def check_contextual_nudge_triggers(self, user_id: str, recent_message: str) -> Optional[datetime]:
        """Check if recent message should trigger a contextual nudge"""
        try:
            message_lower = recent_message.lower()
            
            for trigger_name, trigger_config in self.context_triggers.items():
                # Check if any trigger keywords are present
                if any(keyword in message_lower for keyword in trigger_config['keywords']):
                    # Schedule a nudge for later
                    nudge_time = datetime.now() + timedelta(minutes=trigger_config['delay_minutes'])
                    
                    # Store the contextual nudge
                    await self._store_contextual_nudge(user_id, nudge_time, trigger_name, recent_message)
                    
                    return nudge_time
            
            return None
            
        except Exception as e:
            return None
    
    async def get_due_nudges(self, user_id: str, current_time: datetime) -> List[Dict[str, Any]]:
        """Get nudges that are due for delivery"""
        try:
            results = await self.db.execute_query(
                """SELECT * FROM scheduled_nudges 
                   WHERE user_id = ? AND scheduled_time <= ? AND delivered = 0
                   ORDER BY scheduled_time ASC""",
                (user_id, current_time)
            )
            
            due_nudges = []
            for row in results:
                nudge_data = {
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'scheduled_time': datetime.fromisoformat(row['scheduled_time']),
                    'nudge_type': row['nudge_type'],
                    'context': self.db.deserialize_json(row.get('context', '{}')),
                    'trigger_message': row.get('trigger_message')
                }
                due_nudges.append(nudge_data)
            
            return due_nudges
            
        except Exception as e:
            return []
    
    async def mark_nudge_delivered(self, nudge_id: str) -> None:
        """Mark a nudge as delivered"""
        try:
            await self.db.execute_update(
                "UPDATE scheduled_nudges SET delivered = 1, delivered_at = ? WHERE id = ?",
                (datetime.now(), nudge_id)
            )
        except Exception as e:
            pass
    
    async def _analyze_user_activity_pattern(self, user_id: str) -> Dict[str, Any]:
        """Analyze user's activity patterns from timeline"""
        try:
            # Get recent timeline entries
            cutoff_date = datetime.now() - timedelta(days=14)
            
            results = await self.db.execute_query(
                """SELECT timestamp, entry_type, emotional_state, context_data 
                   FROM timeline_entries 
                   WHERE user_id = ? AND timestamp >= ?
                   ORDER BY timestamp DESC""",
                (user_id, cutoff_date)
            )
            
            if not results:
                return {'activity_hours': [], 'common_emotions': [], 'response_times': []}
            
            # Analyze activity hours
            activity_hours = []
            common_emotions = []
            
            for row in results:
                timestamp = datetime.fromisoformat(row['timestamp'])
                activity_hours.append(timestamp.hour)
                
                emotional_state = self.db.deserialize_json(row.get('emotional_state'))
                if emotional_state and 'primary_emotion' in emotional_state:
                    common_emotions.append(emotional_state['primary_emotion'])
            
            return {
                'activity_hours': activity_hours,
                'common_emotions': common_emotions,
                'total_entries': len(results)
            }
            
        except Exception as e:
            return {'activity_hours': [], 'common_emotions': [], 'response_times': []}
    
    def _classify_user_schedule_type(self, pattern: Dict[str, Any]) -> str:
        """Classify user's schedule type based on activity patterns"""
        activity_hours = pattern.get('activity_hours', [])
        
        if not activity_hours:
            return 'regular_schedule'
        
        # Calculate average activity time
        avg_hour = sum(activity_hours) / len(activity_hours)
        
        # Count early vs late activity
        early_activity = sum(1 for hour in activity_hours if 6 <= hour <= 10)
        late_activity = sum(1 for hour in activity_hours if 22 <= hour <= 24 or 0 <= hour <= 2)
        
        early_ratio = early_activity / len(activity_hours)
        late_ratio = late_activity / len(activity_hours)
        
        if early_ratio > 0.4:
            return 'morning_person'
        elif late_ratio > 0.3:
            return 'night_owl'
        elif len(set(activity_hours)) > 8:  # Very varied schedule
            return 'flexible'
        else:
            return 'regular_schedule'
    
    def _determine_nudge_category(self, context: Dict[str, Any]) -> str:
        """Determine appropriate nudge category based on context"""
        current_hour = datetime.now().hour
        
        # Time-based categories
        if 6 <= current_hour <= 11:
            return 'morning'
        elif 18 <= current_hour <= 23:
            return 'evening'
        
        # Context-based categories
        trigger_type = context.get('trigger_type')
        if trigger_type in ['post_workout', 'work_completion']:
            return 'achievement'
        elif trigger_type == 'stress_relief':
            return 'stress_relief'
        
        return 'general'
    
    async def _generate_nudge_follow_up(self, user_id: str, response: str, 
                                      emotion_profile: EmotionProfile, 
                                      activity_context: ActivityContext) -> str:
        """Generate appropriate follow-up to nudge response"""
        try:
            # Get user's tone profile
            tone_profile = await self.tone_manager.build_user_profile(user_id)
            
            # Generate context-appropriate follow-up
            if emotion_profile.primary_emotion in ['excitement', 'joy', 'accomplishment']:
                base_message = f"Love that {emotion_profile.primary_emotion}! I've captured this moment - you were {activity_context.primary_activity} and feeling {emotion_profile.primary_emotion}. Want me to remind you about this feeling sometime when you need a boost?"
            elif emotion_profile.primary_emotion in ['stress', 'anxiety', 'overwhelmed']:
                base_message = f"I can sense you're feeling {emotion_profile.primary_emotion} right now. I've saved this moment. Remember, these feelings pass, and I'll help you track your emotional journey."
            elif emotion_profile.primary_emotion in ['contentment', 'peaceful', 'relaxed']:
                base_message = f"This sounds like a nice moment of {emotion_profile.primary_emotion}. I've captured it for you - sometimes it's good to remember the quiet, peaceful times too."
            else:
                base_message = f"Thanks for sharing! I've captured this moment - you were {activity_context.primary_activity} and feeling {emotion_profile.primary_emotion}. These snapshots of your life are building your personal timeline."
            
            # Adapt tone
            adapted_message = await self.tone_manager.adapt_response_tone(base_message, tone_profile)
            
            return adapted_message
            
        except Exception as e:
            return "Thanks for sharing! I've captured this moment in your timeline. ✨"
    
    async def _learn_from_nudge_interaction(self, user_id: str, response: str, 
                                          emotion_profile: EmotionProfile, 
                                          nudge_context: Dict[str, Any]) -> None:
        """Learn from nudge interaction to improve future nudging"""
        try:
            # Store interaction data for learning
            interaction_data = {
                'user_id': user_id,
                'timestamp': datetime.now(),
                'nudge_context': nudge_context,
                'response_length': len(response),
                'emotional_response': emotion_profile.primary_emotion,
                'response_positivity': 1 if emotion_profile.primary_emotion in ['joy', 'excitement', 'contentment'] else 0
            }
            
            await self.db.execute_update(
                """INSERT INTO nudge_interactions 
                   (user_id, timestamp, context_data, response_quality, emotional_response)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    user_id,
                    datetime.now(),
                    self.db.serialize_json(interaction_data),
                    len(response),  # Response length as quality indicator
                    emotion_profile.primary_emotion
                )
            )
            
        except Exception as e:
            # Fail silently to not disrupt user experience
            pass
    
    async def _store_scheduled_nudges(self, user_id: str, scheduled_times: List[datetime]) -> None:
        """Store scheduled nudges in database"""
        try:
            # First, clear any existing undelivered nudges for today
            today = datetime.now().date()
            await self.db.execute_update(
                """DELETE FROM scheduled_nudges 
                   WHERE user_id = ? AND DATE(scheduled_time) = ? AND delivered = 0""",
                (user_id, today)
            )
            
            # Insert new scheduled nudges
            for scheduled_time in scheduled_times:
                nudge_id = f"daily_nudge_{user_id}_{scheduled_time.timestamp()}"
                await self.db.execute_update(
                    """INSERT INTO scheduled_nudges 
                       (id, user_id, scheduled_time, nudge_type, context, delivered)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        nudge_id,
                        user_id,
                        scheduled_time,
                        'daily',
                        self.db.serialize_json({}),
                        0
                    )
                )
                
        except Exception as e:
            pass
    
    async def _store_contextual_nudge(self, user_id: str, nudge_time: datetime, 
                                    trigger_type: str, trigger_message: str) -> None:
        """Store a contextual nudge triggered by user activity"""
        try:
            nudge_id = f"contextual_nudge_{user_id}_{nudge_time.timestamp()}"
            context = {
                'trigger_type': trigger_type,
                'trigger_message': trigger_message
            }
            
            await self.db.execute_update(
                """INSERT INTO scheduled_nudges 
                   (id, user_id, scheduled_time, nudge_type, context, trigger_message, delivered)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    nudge_id,
                    user_id,
                    nudge_time,
                    'contextual',
                    self.db.serialize_json(context),
                    trigger_message,
                    0
                )
            )
            
        except Exception as e:
            pass