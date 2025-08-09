"""
Data models for Time Capsule AI
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class CompletionStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    SNOOZED = "snoozed"
    CANCELLED = "cancelled"

class MessageType(Enum):
    REMINDER = "reminder"
    SEARCH = "search"
    CAPSULE = "capsule"
    GENERAL_CHAT = "general_chat"
    NUDGE_RESPONSE = "nudge_response"

@dataclass
class EmotionProfile:
    primary_emotion: str
    intensity: float  # 0.0 to 1.0
    secondary_emotions: Dict[str, float]
    confidence_score: float
    detected_indicators: List[str]
    contextual_factors: Dict[str, Any]

@dataclass
class ActivityContext:
    primary_activity: str
    location_type: str  # home, work, gym, commute, etc.
    social_context: str  # alone, with_friends, family, colleagues
    time_context: str   # morning_routine, work_hours, evening_wind_down
    energy_level: str   # high, medium, low
    detected_keywords: List[str]

@dataclass
class ToneAdjustment:
    formality_shift: float  # -1.0 to 1.0
    energy_shift: float
    support_shift: float
    playfulness_shift: float

@dataclass
class ToneProfile:
    user_id: str
    preferred_formality: float  # -1.0 (casual) to 1.0 (formal)
    preferred_energy: float     # -1.0 (calm) to 1.0 (enthusiastic)
    preferred_support: float    # -1.0 (neutral) to 1.0 (empathetic)
    preferred_playfulness: float # -1.0 (serious) to 1.0 (humorous)
    time_based_preferences: Dict[str, ToneAdjustment]
    context_based_preferences: Dict[str, ToneAdjustment]
    learning_confidence: float
    last_updated: datetime

@dataclass
class UserResponse:
    timestamp: datetime
    response_text: str
    response_time_seconds: int
    sentiment: str  # positive, negative, neutral

@dataclass
class ReminderData:
    id: str
    user_id: str
    content: str
    created_at: datetime
    due_at: datetime
    emotional_context: EmotionProfile
    activity_context: ActivityContext
    location_context: Optional[Dict[str, Any]] = None
    completion_status: CompletionStatus = CompletionStatus.PENDING
    delivery_count: int = 0
    user_response_history: List[UserResponse] = field(default_factory=list)

@dataclass
class TimelineEntry:
    id: str
    user_id: str
    timestamp: datetime
    entry_type: str  # reminder, activity, interaction, capsule
    content: str
    emotional_state: EmotionProfile
    context: Dict[str, Any]
    related_entries: List[str]  # IDs of related timeline entries
    searchable_text: str
    tags: List[str]

@dataclass
class TimeCapsule:
    id: str
    user_id: str
    content: str
    created_at: datetime
    earliest_delivery: datetime
    latest_delivery: datetime
    delivered_at: Optional[datetime]
    emotional_snapshot: EmotionProfile
    context_snapshot: Dict[str, Any]

@dataclass
class ReminderIntent:
    cleaned_message: str
    intent_confidence: float
    extracted_entities: List[str]
    is_reminder: bool

@dataclass
class TemporalData:
    due_datetime: datetime
    confidence: float
    original_expression: str
    is_relative: bool  # "in 2 hours" vs "Monday at 3pm"

@dataclass
class SearchResult:
    entry_id: str
    relevance_score: float
    content_snippet: str
    timestamp: datetime
    entry_type: str
    emotional_context: EmotionProfile

@dataclass
class MoodPattern:
    user_id: str
    pattern_type: str  # daily, weekly, situational
    triggers: List[str]
    emotional_progression: List[EmotionProfile]
    confidence: float
    detected_at: datetime

@dataclass
class ShareableContent:
    content_type: str  # text, image_card
    content: str
    privacy_level: str  # public, friends, private
    platform_optimized: Dict[str, str]  # different versions for different platforms