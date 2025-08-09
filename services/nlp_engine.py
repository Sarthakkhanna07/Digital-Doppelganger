"""
Natural Language Processing Engine for Time Capsule AI
Handles intent classification, temporal parsing, and context extraction
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import asyncio

from models import ReminderIntent, TemporalData, ActivityContext, MessageType

class NLPEngine:
    def __init__(self):
        self.reminder_keywords = [
            "remind", "remember", "don't forget", "make sure", "need to",
            "have to", "should", "must", "later", "tomorrow", "next week"
        ]
        
        self.temporal_patterns = {
            # Relative time patterns
            r'in (\d+) (minute|hour|day|week|month)s?': self._parse_relative_time,
            r'(\d+) (minute|hour|day|week|month)s? from now': self._parse_relative_time,
            r'tomorrow': lambda: datetime.now() + timedelta(days=1),
            r'next week': lambda: datetime.now() + timedelta(weeks=1),
            r'next month': lambda: datetime.now() + timedelta(days=30),
            
            # Specific day patterns
            r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)': self._parse_weekday,
            r'on (monday|tuesday|wednesday|thursday|friday|saturday|sunday)': self._parse_weekday,
            
            # Time patterns
            r'at (\d{1,2}):?(\d{2})?\s?(am|pm)?': self._parse_time,
            r'(\d{1,2})\s?(am|pm)': self._parse_time,
        }
        
        self.activity_keywords = {
            'work': ['work', 'office', 'meeting', 'project', 'deadline', 'boss', 'colleague'],
            'exercise': ['workout', 'gym', 'run', 'exercise', 'fitness', 'training'],
            'home': ['home', 'house', 'family', 'cooking', 'cleaning', 'relaxing'],
            'commute': ['driving', 'train', 'bus', 'commute', 'traffic', 'traveling'],
            'social': ['friends', 'party', 'dinner', 'hanging out', 'date', 'social'],
            'health': ['doctor', 'appointment', 'medicine', 'sick', 'tired', 'stressed']
        }
        
        self.emotion_indicators = {
            'stress': ['stressed', 'overwhelmed', 'anxious', 'worried', 'pressure'],
            'excitement': ['excited', 'thrilled', 'pumped', 'can\'t wait', 'amazing'],
            'accomplishment': ['finished', 'completed', 'achieved', 'proud', 'done'],
            'tired': ['tired', 'exhausted', 'drained', 'sleepy', 'worn out'],
            'happy': ['happy', 'great', 'awesome', 'fantastic', 'wonderful'],
            'sad': ['sad', 'down', 'disappointed', 'upset', 'bummed']
        }
    
    async def parse_reminder_intent(self, message: str) -> ReminderIntent:
        """Parse a message to determine if it's a reminder and extract intent"""
        message_lower = message.lower()
        
        # Check for reminder keywords
        reminder_score = 0
        for keyword in self.reminder_keywords:
            if keyword in message_lower:
                reminder_score += 1
        
        # Check for temporal expressions
        temporal_score = 0
        for pattern in self.temporal_patterns.keys():
            if re.search(pattern, message_lower):
                temporal_score += 1
        
        # Calculate confidence (better scoring system)
        confidence = 0.0
        if reminder_score > 0:
            confidence += 0.6  # Base confidence for reminder keywords
        if temporal_score > 0:
            confidence += 0.4  # Additional confidence for temporal expressions
        
        # Normalize to 0-1 range
        confidence = min(confidence, 1.0)
        
        # Extract entities (simple keyword extraction for now)
        entities = []
        words = message.split()
        for word in words:
            if word.lower() in ['call', 'email', 'buy', 'send', 'finish', 'start']:
                entities.append(word)
        
        # Clean the message (remove reminder trigger words for storage)
        cleaned_message = message
        for trigger in ['remind me to', 'remember to', 'don\'t forget to']:
            cleaned_message = re.sub(trigger, '', cleaned_message, flags=re.IGNORECASE).strip()
        
        return ReminderIntent(
            cleaned_message=cleaned_message,
            intent_confidence=confidence,
            extracted_entities=entities,
            is_reminder=confidence > 0.3
        )
    
    async def extract_temporal_info(self, message: str) -> TemporalData:
        """Extract temporal information from message"""
        message_lower = message.lower()
        
        # Default to 1 hour from now if no time specified
        default_time = datetime.now() + timedelta(hours=1)
        
        for pattern, parser in self.temporal_patterns.items():
            match = re.search(pattern, message_lower)
            if match:
                try:
                    if callable(parser):
                        if pattern in [r'tomorrow', r'next week', r'next month']:
                            due_time = parser()
                        else:
                            due_time = parser(match)
                    else:
                        due_time = default_time
                    
                    return TemporalData(
                        due_datetime=due_time,
                        confidence=0.8,
                        original_expression=match.group(0),
                        is_relative='in ' in match.group(0) or 'from now' in match.group(0)
                    )
                except Exception:
                    continue
        
        # No temporal expression found
        return TemporalData(
            due_datetime=default_time,
            confidence=0.2,
            original_expression="",
            is_relative=True
        )
    
    async def detect_activity_context(self, message: str) -> ActivityContext:
        """Detect activity and context from message"""
        message_lower = message.lower()
        
        # Detect primary activity
        activity_scores = {}
        for activity, keywords in self.activity_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > 0:
                activity_scores[activity] = score
        
        primary_activity = max(activity_scores, key=activity_scores.get) if activity_scores else "general"
        
        # Detect location type (simple heuristics)
        location_type = "unknown"
        if any(word in message_lower for word in ['home', 'house']):
            location_type = "home"
        elif any(word in message_lower for word in ['work', 'office']):
            location_type = "work"
        elif any(word in message_lower for word in ['gym', 'workout']):
            location_type = "gym"
        
        # Detect social context
        social_context = "alone"
        if any(word in message_lower for word in ['friends', 'family', 'colleagues']):
            social_context = "with_others"
        
        # Detect time context based on current time
        current_hour = datetime.now().hour
        if 6 <= current_hour < 12:
            time_context = "morning_routine"
        elif 12 <= current_hour < 17:
            time_context = "work_hours"
        elif 17 <= current_hour < 22:
            time_context = "evening_wind_down"
        else:
            time_context = "late_night"
        
        # Detect energy level from language
        energy_level = "medium"
        if any(word in message_lower for word in ['tired', 'exhausted', 'drained']):
            energy_level = "low"
        elif any(word in message_lower for word in ['excited', 'pumped', 'energetic']):
            energy_level = "high"
        
        return ActivityContext(
            primary_activity=primary_activity,
            location_type=location_type,
            social_context=social_context,
            time_context=time_context,
            energy_level=energy_level,
            detected_keywords=list(activity_scores.keys())
        )
    
    async def classify_message_type(self, message: str) -> MessageType:
        """Classify the type of message"""
        message_lower = message.lower()
        
        # Check for search intent
        if any(word in message_lower for word in ['search', 'find', 'look for', 'show me']):
            return MessageType.SEARCH
        
        # Check for time capsule intent
        if any(word in message_lower for word in ['capsule', 'save this moment', 'remember this']):
            return MessageType.CAPSULE
        
        # Check for reminder intent
        reminder_intent = await self.parse_reminder_intent(message)
        if reminder_intent.is_reminder:
            return MessageType.REMINDER
        
        # Default to general chat
        return MessageType.GENERAL_CHAT
    
    def _parse_relative_time(self, match) -> datetime:
        """Parse relative time expressions like 'in 2 hours'"""
        try:
            number = int(match.group(1))
            unit = match.group(2)
            
            if unit.startswith('minute'):
                return datetime.now() + timedelta(minutes=number)
            elif unit.startswith('hour'):
                return datetime.now() + timedelta(hours=number)
            elif unit.startswith('day'):
                return datetime.now() + timedelta(days=number)
            elif unit.startswith('week'):
                return datetime.now() + timedelta(weeks=number)
            elif unit.startswith('month'):
                return datetime.now() + timedelta(days=number * 30)
        except (ValueError, AttributeError):
            pass
        
        return datetime.now() + timedelta(hours=1)
    
    def _parse_weekday(self, match) -> datetime:
        """Parse weekday expressions like 'Monday'"""
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        try:
            target_weekday = weekdays[match.group(1).lower()]
            current_weekday = datetime.now().weekday()
            
            days_ahead = target_weekday - current_weekday
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            
            return datetime.now() + timedelta(days=days_ahead)
        except (KeyError, AttributeError):
            return datetime.now() + timedelta(days=1)
    
    def _parse_time(self, match) -> datetime:
        """Parse time expressions like '3pm' or '15:30'"""
        try:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            am_pm = match.group(3).lower() if match.group(3) else None
            
            if am_pm == 'pm' and hour != 12:
                hour += 12
            elif am_pm == 'am' and hour == 12:
                hour = 0
            
            target_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If the time has already passed today, schedule for tomorrow
            if target_time <= datetime.now():
                target_time += timedelta(days=1)
            
            return target_time
        except (ValueError, AttributeError):
            return datetime.now() + timedelta(hours=1)