"""
Time Capsule AI - MCP Server for Puch AI Integration
A revolutionary reminder system that captures emotional context and delivers personalized experiences.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Annotated, Optional, List
import json
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp import ErrorData, McpError
from mcp.server.auth.provider import AccessToken
from mcp.types import TextContent, ImageContent, INVALID_PARAMS, INTERNAL_ERROR
from pydantic import BaseModel, Field

from models import ReminderData, EmotionProfile, ActivityContext, ToneProfile, TimelineEntry, TimeCapsule, ShareableContent, CompletionStatus
from services.nlp_engine import NLPEngine
from services.emotion_analyzer import EmotionAnalyzer
from services.tone_manager import ToneManager
from services.data_manager import DataManager
from services.nudge_manager import NudgeManager
from services.social_sharing import SocialSharingManager
from services.scheduler import ReminderScheduler, PuchAIDelivery, ConsoleDelivery
from utils.database import DatabaseManager

# Load environment variables
load_dotenv()

TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")
DATABASE_URL = os.environ.get("DATABASE_URL", "time_capsule.db")

assert TOKEN is not None, "Please set AUTH_TOKEN in your .env file"
assert MY_NUMBER is not None, "Please set MY_NUMBER in your .env file"

# Public MCP Server Mode - Anyone can use this server
PUBLIC_MODE = os.environ.get("PUBLIC_MODE", "true").lower() == "true"

if PUBLIC_MODE:
    print("🌍 Running in PUBLIC MODE - Anyone can connect!")
else:
    print("🔒 Running in PRIVATE MODE - Personal use only")

# Auth Provider - Exact pattern from working Puch AI examples
class TimeCapsuleAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(
                token=token,
                client_id="puch-client",
                scopes=["*"],
                expires_at=None,
            )
        return None

# Rich Tool Description for Time Capsule AI
class TimeCapsuleToolDescription(BaseModel):
    description: str
    use_when: str
    emotional_context: str
    side_effects: str | None = None

# Initialize services
db_manager = DatabaseManager(DATABASE_URL)
data_manager = DataManager(db_manager)
nlp_engine = NLPEngine()
emotion_analyzer = EmotionAnalyzer()
tone_manager = ToneManager(data_manager)
nudge_manager = NudgeManager(data_manager, tone_manager, emotion_analyzer)
social_sharing = SocialSharingManager(data_manager)

# Initialize automatic scheduler
scheduler = ReminderScheduler(data_manager, tone_manager)

# Setup delivery methods
console_delivery = ConsoleDelivery()
scheduler.add_delivery_callback(console_delivery.deliver_to_console)

# Setup Puch AI webhook delivery for automatic reminders
PUCH_WEBHOOK_URL = os.environ.get("PUCH_WEBHOOK_URL")
if PUCH_WEBHOOK_URL:
    puch_delivery = PuchAIDelivery(PUCH_WEBHOOK_URL, TOKEN)
    scheduler.add_delivery_callback(puch_delivery.deliver_to_puch_ai)
    print("🔗 Puch AI webhook delivery enabled!")
else:
    print("💡 To enable automatic WhatsApp delivery, set PUCH_WEBHOOK_URL in your .env file")

# MCP Server Setup - Following Puch AI example pattern
mcp = FastMCP(
    "Time Capsule AI - Emotional Memory Assistant",
    auth=TimeCapsuleAuthProvider(TOKEN),
)

# Required validation tool for Puch AI
# Required validation tool for Puch AI
@mcp.tool
async def validate() -> str:
    """Validation tool required by Puch AI"""
    return MY_NUMBER



# Manual trigger for testing automatic delivery
@mcp.tool
async def trigger_delivery_check() -> str:
    """Manually trigger a check for due reminders, nudges, and time capsules (for testing)"""
    try:
        # Force a delivery check
        await scheduler._check_and_deliver_reminders()
        await scheduler._check_and_deliver_nudges()
        await scheduler._check_and_deliver_time_capsules()
        
        return "✅ Manual delivery check completed! Check console for any delivered messages."
    except Exception as e:
        return f"❌ Error during manual delivery check: {str(e)}"

# Core Time Capsule AI Tools
CREATE_REMINDER_DESCRIPTION = TimeCapsuleToolDescription(
    description="Create a context-rich reminder that captures your current emotional state and situation",
    use_when="When user wants to set a reminder with emotional and contextual memory",
    emotional_context="Captures mood, activity, and personal context for future replay",
    side_effects="Stores reminder with full emotional and situational context in timeline"
)

@mcp.tool(description=CREATE_REMINDER_DESCRIPTION.model_dump_json())
async def create_reminder(
    message: Annotated[str, Field(description="The reminder message from the user")],
    user_context: Annotated[str, Field(description="Current user context and situation")] = "",
    due_time: Annotated[str, Field(description="When to deliver the reminder (natural language)")] = ""
) -> str:
    """
    Creates a context-rich reminder that captures emotional state and situation.
    This is the core feature that makes reminders feel like messages from your past self.
    """
    try:
        # Extract user ID from context (in real implementation, this would come from Puch AI)
        user_id = "default_user"  # TODO: Get from Puch AI context
        
        # Process the message with NLP
        reminder_intent = await nlp_engine.parse_reminder_intent(message)
        temporal_data = await nlp_engine.extract_temporal_info(due_time or message)
        activity_context = await nlp_engine.detect_activity_context(user_context + " " + message)
        
        # Analyze emotional state
        emotion_profile = await emotion_analyzer.analyze_emotion(message, {
            "user_context": user_context,
            "time_of_day": datetime.now().strftime("%H:%M"),
            "day_of_week": datetime.now().strftime("%A")
        })
        
        # Create reminder data
        reminder_data = ReminderData(
            id=f"reminder_{datetime.now().timestamp()}",
            user_id=user_id,
            content=reminder_intent.cleaned_message,
            created_at=datetime.now(),
            due_at=temporal_data.due_datetime,
            emotional_context=emotion_profile,
            activity_context=activity_context,
            completion_status=CompletionStatus.PENDING,
            delivery_count=0,
            user_response_history=[]
        )
        
        # Store the reminder
        reminder_id = await data_manager.store_reminder(reminder_data)
        
        # Get user's tone profile for response
        tone_profile = await tone_manager.build_user_profile(user_id)
        
        # Generate contextual confirmation
        confirmation = await tone_manager.adapt_response_tone(
            f"Got it! I'll remind you about '{reminder_intent.cleaned_message}' on {temporal_data.due_datetime.strftime('%A, %B %d at %I:%M %p')}. "
            f"I can sense you're feeling {emotion_profile.primary_emotion} right now while {activity_context.primary_activity}. "
            f"When I remind you, I'll include this context so you remember exactly how you felt when you set this reminder.",
            tone_profile
        )
        
        return confirmation
        
    except Exception as e:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Failed to create reminder: {str(e)}"))

GET_DUE_REMINDERS_DESCRIPTION = TimeCapsuleToolDescription(
    description="Retrieve reminders that are due with full emotional and contextual replay",
    use_when="When checking for due reminders or when Puch AI needs to deliver scheduled reminders",
    emotional_context="Recreates the original moment and emotional state when reminder was created",
    side_effects="Updates delivery count and logs user interaction"
)

@mcp.tool(description=GET_DUE_REMINDERS_DESCRIPTION.model_dump_json())
async def get_due_reminders(
    user_id: Annotated[str, Field(description="User identifier")] = "default_user"
) -> str:
    """
    Gets due reminders with rich emotional context - the magic of Time Capsule AI.
    Each reminder includes the story of when it was created.
    """
    try:
        # Get due reminders
        due_reminders = await data_manager.get_due_reminders(user_id, datetime.now())
        
        if not due_reminders:
            return "No reminders due right now. You're all caught up! 🎉"
        
        # Get user's current tone profile
        tone_profile = await tone_manager.build_user_profile(user_id)
        
        responses = []
        for reminder in due_reminders:
            # Calculate time elapsed
            time_elapsed = datetime.now() - reminder.created_at
            time_ago = _format_time_elapsed(time_elapsed)
            
            # Create rich contextual reminder
            context_story = _build_context_story(reminder, time_ago)
            
            # Adapt tone for delivery
            adapted_message = await tone_manager.adapt_response_tone(context_story, tone_profile)
            
            responses.append(adapted_message)
            
            # Update delivery count
            await data_manager.update_reminder_delivery(reminder.id)
        
        return "\n\n---\n\n".join(responses)
        
    except Exception as e:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Failed to get due reminders: {str(e)}"))

def _format_time_elapsed(delta: timedelta) -> str:
    """Format time elapsed in a human-friendly way"""
    if delta.days > 0:
        return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
    elif delta.seconds > 3600:
        hours = delta.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif delta.seconds > 60:
        minutes = delta.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "just now"

def _build_context_story(reminder: ReminderData, time_ago: str) -> str:
    """Build the magical context story that makes reminders feel personal"""
    emotion_desc = _describe_emotion(reminder.emotional_context)
    activity_desc = _describe_activity(reminder.activity_context)
    
    story = f"🕰️ **{time_ago.title()}**, you were {activity_desc} and {emotion_desc} when you told me:\n\n"
    story += f"💭 *\"{reminder.content}\"*\n\n"
    story += f"✨ That was {time_ago} - here's your reminder with the full story of that moment!"
    
    return story

def _describe_emotion(emotion: EmotionProfile) -> str:
    """Convert emotion profile to natural description"""
    intensity_words = {
        0.8: "really", 0.6: "quite", 0.4: "somewhat", 0.2: "a bit"
    }
    intensity = max([k for k in intensity_words.keys() if emotion.intensity >= k], default=0.2)
    return f"feeling {intensity_words[intensity]} {emotion.primary_emotion}"

def _describe_activity(activity: ActivityContext) -> str:
    """Convert activity context to natural description"""
    location_map = {
        "home": "at home",
        "work": "at work", 
        "gym": "at the gym",
        "commute": "commuting"
    }
    location = location_map.get(activity.location_type, activity.location_type)
    return f"{activity.primary_activity} {location}"

# Active Nudging Tools
DAILY_NUDGE_DESCRIPTION = TimeCapsuleToolDescription(
    description="Send a proactive daily nudge to capture life moments",
    use_when="When it's time for a scheduled daily check-in with the user",
    emotional_context="Proactively captures current mood and activity for timeline building",
    side_effects="Creates timeline entry and learns user patterns for better future nudging"
)

@mcp.tool(description=DAILY_NUDGE_DESCRIPTION.model_dump_json())
async def daily_nudge(
    user_id: Annotated[str, Field(description="User identifier")] = "default_user"
) -> str:
    """
    Send a proactive daily nudge to capture current life moments.
    This is the magic that makes Time Capsule AI feel alive and caring.
    """
    try:
        # Generate personalized nudge message
        nudge_message = await nudge_manager.generate_nudge_message(user_id)
        
        # Check for any contextual triggers that might influence the nudge
        context = {
            "nudge_type": "daily",
            "time_of_day": datetime.now().strftime("%H:%M"),
            "day_of_week": datetime.now().strftime("%A")
        }
        
        return nudge_message
        
    except Exception as e:
        # Fallback to simple nudge
        return "Hey, what are you doing right now? Want me to save this moment for later?"

PROCESS_NUDGE_RESPONSE_DESCRIPTION = TimeCapsuleToolDescription(
    description="Process user's response to a nudge and capture the moment",
    use_when="When user responds to a daily nudge or proactive check-in",
    emotional_context="Captures and analyzes the user's current emotional state and activity",
    side_effects="Creates timeline entry, learns user patterns, may offer to create reminders"
)

@mcp.tool(description=PROCESS_NUDGE_RESPONSE_DESCRIPTION.model_dump_json())
async def process_nudge_response(
    user_response: Annotated[str, Field(description="User's response to the nudge")],
    user_id: Annotated[str, Field(description="User identifier")] = "default_user"
) -> str:
    """
    Process user's response to a nudge and create a meaningful timeline entry.
    This builds the user's personal life log with emotional context.
    """
    try:
        # Process the nudge response
        nudge_context = {
            "nudge_type": "daily",
            "timestamp": datetime.now().isoformat()
        }
        
        follow_up = await nudge_manager.process_nudge_response(user_id, user_response, nudge_context)
        
        # Check if this response should trigger a contextual nudge later
        future_nudge = await nudge_manager.check_contextual_nudge_triggers(user_id, user_response)
        
        if future_nudge:
            follow_up += f"\n\n(I'll check in with you later to see how things are going! 😊)"
        
        return follow_up
        
    except Exception as e:
        return "Thanks for sharing! I've captured this moment in your timeline. ✨"

SCHEDULE_NUDGES_DESCRIPTION = TimeCapsuleToolDescription(
    description="Schedule optimal daily nudges based on user patterns",
    use_when="When setting up or updating a user's nudge schedule",
    emotional_context="Learns user activity patterns to find optimal engagement times",
    side_effects="Creates scheduled nudges in database based on user's activity patterns"
)

@mcp.tool(description=SCHEDULE_NUDGES_DESCRIPTION.model_dump_json())
async def schedule_nudges(
    user_id: Annotated[str, Field(description="User identifier")] = "default_user"
) -> str:
    """
    Schedule optimal daily nudges based on user's activity patterns.
    This makes the AI feel proactive and personally attuned.
    """
    try:
        # Schedule nudges based on user patterns
        scheduled_times = await nudge_manager.schedule_daily_nudges(user_id)
        
        # Format response
        if len(scheduled_times) == 1:
            time_str = scheduled_times[0].strftime("%I:%M %p")
            return f"Perfect! I've scheduled a daily check-in for around {time_str}. I'll learn your patterns and adjust the timing to work better for you over time. 🕰️"
        else:
            times_str = ", ".join([t.strftime("%I:%M %p") for t in scheduled_times])
            return f"Great! I've scheduled daily check-ins for around {times_str}. These times are based on when you're usually active, and I'll keep learning to make them even better! 🕰️"
        
    except Exception as e:
        return "I've set up daily check-ins for you! I'll learn your patterns and find the perfect times to capture your life moments. 🕰️"

GET_DUE_NUDGES_DESCRIPTION = TimeCapsuleToolDescription(
    description="Get nudges that are due for delivery to users",
    use_when="When checking for scheduled nudges that need to be sent",
    emotional_context="Delivers proactive engagement at optimal times",
    side_effects="Marks nudges as delivered and triggers user engagement"
)

@mcp.tool(description=GET_DUE_NUDGES_DESCRIPTION.model_dump_json())
async def get_due_nudges(
    user_id: Annotated[str, Field(description="User identifier")] = "default_user"
) -> str:
    """
    Get nudges that are due for delivery. This enables proactive engagement.
    """
    try:
        # Get due nudges
        due_nudges = await nudge_manager.get_due_nudges(user_id, datetime.now())
        
        if not due_nudges:
            return "No nudges due right now."
        
        responses = []
        for nudge in due_nudges:
            # Generate nudge message
            nudge_message = await nudge_manager.generate_nudge_message(
                user_id, 
                nudge.get('context', {})
            )
            
            responses.append(nudge_message)
            
            # Mark as delivered
            await nudge_manager.mark_nudge_delivered(nudge['id'])
        
        return "\n\n".join(responses)
        
    except Exception as e:
        return "Hey, what are you doing right now? Want me to save this moment for later?"

# Timeline Search and Discovery Tools
SEARCH_TIMELINE_DESCRIPTION = TimeCapsuleToolDescription(
    description="Search through user's personal timeline and life log",
    use_when="When user wants to find past moments, emotions, or activities",
    emotional_context="Helps users rediscover patterns, memories, and personal insights",
    side_effects="Returns chronological results with emotional and contextual details"
)

@mcp.tool(description=SEARCH_TIMELINE_DESCRIPTION.model_dump_json())
async def search_timeline(
    query: Annotated[str, Field(description="Search query (keywords, emotions, activities, or dates)")],
    user_id: Annotated[str, Field(description="User identifier")] = "default_user",
    limit: Annotated[int, Field(description="Maximum number of results to return")] = 10
) -> str:
    """
    Search through user's personal timeline - like having a searchable life log.
    This is where Time Capsule AI becomes a personal memory assistant.
    """
    try:
        # Perform timeline search
        search_results = await data_manager.search_timeline(user_id, query, limit)
        
        if not search_results:
            return f"I couldn't find any moments matching '{query}' in your timeline. Try a different search term or create some new memories! 🔍"
        
        # Format results with rich context
        formatted_results = []
        for i, result in enumerate(search_results, 1):
            # Calculate time ago
            time_elapsed = datetime.now() - result.timestamp
            time_ago = _format_time_elapsed(time_elapsed)
            
            # Format result with emotional context
            emotion_desc = f"feeling {result.emotional_context.primary_emotion}"
            
            result_text = f"**{i}. {time_ago.title()}** ({result.timestamp.strftime('%B %d, %Y')})\n"
            result_text += f"   💭 *{result.content_snippet}*\n"
            result_text += f"   🎭 You were {emotion_desc}\n"
            result_text += f"   📍 Type: {result.entry_type}\n"
            
            formatted_results.append(result_text)
        
        # Create response with user's tone
        tone_profile = await tone_manager.build_user_profile(user_id)
        
        header = f"🔍 **Found {len(search_results)} moments matching '{query}':**\n\n"
        results_text = "\n".join(formatted_results)
        
        if len(search_results) == limit:
            footer = f"\n💡 *Showing top {limit} results. Try a more specific search for different results.*"
        else:
            footer = f"\n✨ *These are all your moments matching '{query}'. Keep creating memories!*"
        
        full_response = header + results_text + footer
        
        # Adapt tone
        adapted_response = await tone_manager.adapt_response_tone(full_response, tone_profile)
        
        return adapted_response
        
    except Exception as e:
        return f"I had trouble searching your timeline for '{query}'. Let me know if you'd like to try a different search! 🔍"

GET_TIMELINE_DESCRIPTION = TimeCapsuleToolDescription(
    description="Get user's recent timeline entries with emotional journey",
    use_when="When user wants to see their recent life log or emotional patterns",
    emotional_context="Shows personal growth, mood patterns, and life progression",
    side_effects="Returns chronological life entries with full emotional context"
)

@mcp.tool(description=GET_TIMELINE_DESCRIPTION.model_dump_json())
async def get_timeline(
    user_id: Annotated[str, Field(description="User identifier")] = "default_user",
    days_back: Annotated[int, Field(description="Number of days to look back")] = 7
) -> str:
    """
    Get user's recent timeline - their personal life log with emotional context.
    This shows the user their emotional journey and life patterns.
    """
    try:
        # Get timeline entries
        timeline_entries = await data_manager.get_user_timeline(user_id, days_back)
        
        if not timeline_entries:
            return f"Your timeline is empty for the last {days_back} days. Let's start capturing some moments! Use daily nudges or create reminders to build your personal life log. ✨"
        
        # Group entries by date
        entries_by_date = {}
        for entry in timeline_entries:
            date_key = entry.timestamp.date()
            if date_key not in entries_by_date:
                entries_by_date[date_key] = []
            entries_by_date[date_key].append(entry)
        
        # Format timeline
        formatted_timeline = []
        
        for date, entries in sorted(entries_by_date.items(), reverse=True):
            date_str = date.strftime("%A, %B %d, %Y")
            formatted_timeline.append(f"📅 **{date_str}**")
            
            for entry in sorted(entries, key=lambda x: x.timestamp):
                time_str = entry.timestamp.strftime("%I:%M %p")
                emotion_desc = entry.emotional_state.primary_emotion
                
                entry_text = f"   {time_str} - {entry.content[:100]}"
                if len(entry.content) > 100:
                    entry_text += "..."
                entry_text += f" *({emotion_desc})*"
                
                formatted_timeline.append(entry_text)
            
            formatted_timeline.append("")  # Empty line between dates
        
        # Get user's tone profile and adapt response
        tone_profile = await tone_manager.build_user_profile(user_id)
        
        # Analyze emotional patterns
        emotions = [entry.emotional_state.primary_emotion for entry in timeline_entries]
        most_common_emotion = max(set(emotions), key=emotions.count) if emotions else "neutral"
        
        header = f"📖 **Your Life Timeline - Last {days_back} Days**\n\n"
        timeline_text = "\n".join(formatted_timeline)
        
        # Add emotional insights
        insights = f"\n🎭 **Emotional Insights:**\n"
        insights += f"   Most common feeling: {most_common_emotion}\n"
        insights += f"   Total moments captured: {len(timeline_entries)}\n"
        insights += f"   Days with activity: {len(entries_by_date)}\n"
        
        full_response = header + timeline_text + insights
        
        # Adapt tone
        adapted_response = await tone_manager.adapt_response_tone(full_response, tone_profile)
        
        return adapted_response
        
    except Exception as e:
        return f"I had trouble getting your timeline. Let me know if you'd like to try again! 📖"

# Time Capsule Tools
CREATE_TIME_CAPSULE_DESCRIPTION = TimeCapsuleToolDescription(
    description="Create a time capsule to be delivered at a random future time",
    use_when="When user wants to save a special moment for future rediscovery",
    emotional_context="Captures current emotional state and context for future surprise delivery",
    side_effects="Schedules surprise delivery within specified timeframe with full context"
)

@mcp.tool(description=CREATE_TIME_CAPSULE_DESCRIPTION.model_dump_json())
async def create_time_capsule(
    content: Annotated[str, Field(description="The content/message to save in the time capsule")],
    delivery_window: Annotated[str, Field(description="When to deliver (e.g., 'in 1-3 months', 'next year')")] = "in 1-6 months",
    user_id: Annotated[str, Field(description="User identifier")] = "default_user"
) -> str:
    """
    Create a time capsule - a special moment saved for surprise future delivery.
    This is pure magic - rediscovering your past self at unexpected moments.
    """
    try:
        # Parse delivery window
        earliest_delivery, latest_delivery = _parse_delivery_window(delivery_window)
        
        # Analyze current emotional state and context
        emotion_profile = await emotion_analyzer.analyze_emotion(content, {
            "time_of_day": datetime.now().strftime("%H:%M"),
            "day_of_week": datetime.now().strftime("%A"),
            "capsule_creation": True
        })
        
        # Get current activity context
        activity_context = await nlp_engine.detect_activity_context(content)
        
        # Create time capsule
        capsule = TimeCapsule(
            id=f"capsule_{datetime.now().timestamp()}",
            user_id=user_id,
            content=content,
            created_at=datetime.now(),
            earliest_delivery=earliest_delivery,
            latest_delivery=latest_delivery,
            delivered_at=None,
            emotional_snapshot=emotion_profile,
            context_snapshot={
                "activity_context": activity_context.__dict__,
                "creation_time": datetime.now().isoformat(),
                "day_of_week": datetime.now().strftime("%A"),
                "season": _get_current_season(),
                "user_tone_at_creation": (await tone_manager.build_user_profile(user_id)).__dict__
            }
        )
        
        # Store the time capsule
        capsule_id = await data_manager.store_time_capsule(capsule)
        
        # Get user's tone profile for response
        tone_profile = await tone_manager.build_user_profile(user_id)
        
        # Generate confirmation message
        time_range = _format_delivery_window(earliest_delivery, latest_delivery)
        base_message = f"✨ **Time Capsule Created!** ✨\n\n"
        base_message += f"I've captured this moment: *\"{content}\"*\n\n"
        base_message += f"Right now you're feeling {emotion_profile.primary_emotion} while {activity_context.primary_activity}. "
        base_message += f"I'll surprise you with this memory {time_range} - imagine how different you might feel then!\n\n"
        base_message += f"🎁 This will be like getting a message from your {datetime.now().strftime('%B %Y')} self!"
        
        # Adapt tone
        adapted_message = await tone_manager.adapt_response_tone(base_message, tone_profile)
        
        return adapted_message
        
    except Exception as e:
        return f"I had trouble creating your time capsule, but the moment isn't lost! Try again and I'll capture this special memory for future you. ✨"

GET_DUE_TIME_CAPSULES_DESCRIPTION = TimeCapsuleToolDescription(
    description="Get time capsules that are ready for surprise delivery",
    use_when="When checking for time capsules ready to be delivered to users",
    emotional_context="Delivers surprise memories with full original context and emotional state",
    side_effects="Marks capsules as delivered and creates magical rediscovery moments"
)

@mcp.tool(description=GET_DUE_TIME_CAPSULES_DESCRIPTION.model_dump_json())
async def get_due_time_capsules(
    user_id: Annotated[str, Field(description="User identifier")] = "default_user"
) -> str:
    """
    Get time capsules ready for delivery - surprise messages from past self.
    This creates magical moments of rediscovery and personal connection.
    """
    try:
        # Get due time capsules
        due_capsules = await data_manager.get_due_time_capsules(user_id, datetime.now())
        
        if not due_capsules:
            return "No time capsules ready for delivery right now. The surprises are still brewing! ✨"
        
        responses = []
        for capsule in due_capsules:
            # Calculate time elapsed since creation
            time_elapsed = datetime.now() - capsule.created_at
            time_ago = _format_time_elapsed(time_elapsed)
            
            # Get current user tone profile
            current_tone_profile = await tone_manager.build_user_profile(user_id)
            
            # Build the magical delivery message
            delivery_message = _build_time_capsule_delivery(capsule, time_ago, current_tone_profile)
            
            responses.append(delivery_message)
            
            # Mark as delivered
            await data_manager.mark_time_capsule_delivered(capsule.id)
        
        return "\n\n🎁✨🎁✨🎁\n\n".join(responses)
        
    except Exception as e:
        return "I had trouble accessing your time capsules right now. The surprises are still safe and waiting! ✨"

def _parse_delivery_window(window_str: str) -> tuple[datetime, datetime]:
    """Parse delivery window string into datetime range"""
    now = datetime.now()
    
    # Simple parsing for common patterns
    if "month" in window_str.lower():
        if "1-3" in window_str or "1 to 3" in window_str:
            earliest = now + timedelta(days=30)
            latest = now + timedelta(days=90)
        elif "1-6" in window_str or "1 to 6" in window_str:
            earliest = now + timedelta(days=30)
            latest = now + timedelta(days=180)
        elif "3-6" in window_str:
            earliest = now + timedelta(days=90)
            latest = now + timedelta(days=180)
        else:
            # Default to 1-6 months
            earliest = now + timedelta(days=30)
            latest = now + timedelta(days=180)
    elif "year" in window_str.lower():
        earliest = now + timedelta(days=365)
        latest = now + timedelta(days=730)
    elif "week" in window_str.lower():
        earliest = now + timedelta(weeks=1)
        latest = now + timedelta(weeks=4)
    else:
        # Default fallback
        earliest = now + timedelta(days=30)
        latest = now + timedelta(days=180)
    
    return earliest, latest

def _format_delivery_window(earliest: datetime, latest: datetime) -> str:
    """Format delivery window for user display"""
    earliest_months = (earliest - datetime.now()).days // 30
    latest_months = (latest - datetime.now()).days // 30
    
    if earliest_months == latest_months:
        return f"in about {earliest_months} month{'s' if earliest_months != 1 else ''}"
    else:
        return f"sometime between {earliest_months}-{latest_months} months from now"

def _get_current_season() -> str:
    """Get current season"""
    month = datetime.now().month
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "fall"

def _build_time_capsule_delivery(capsule: TimeCapsule, time_ago: str, current_tone: ToneProfile) -> str:
    """Build the magical time capsule delivery message"""
    # Get context from when it was created
    creation_context = capsule.context_snapshot
    emotion_then = capsule.emotional_snapshot.primary_emotion
    
    # Build the story
    delivery_message = f"🎁 **SURPRISE TIME CAPSULE!** 🎁\n\n"
    delivery_message += f"⏰ **{time_ago.title()}**, in {creation_context.get('season', 'unknown')} {capsule.created_at.year}, "
    delivery_message += f"you were feeling {emotion_then} and decided to send a message to future you...\n\n"
    
    delivery_message += f"💭 **Your past self said:**\n"
    delivery_message += f"*\"{capsule.content}\"*\n\n"
    
    delivery_message += f"✨ **What's changed since then:**\n"
    delivery_message += f"   • That was {time_ago}\n"
    delivery_message += f"   • You were in {creation_context.get('season', 'unknown')} {capsule.created_at.year}\n"
    delivery_message += f"   • You were feeling {emotion_then} then\n"
    delivery_message += f"   • It was a {capsule.created_at.strftime('%A')}\n\n"
    
    delivery_message += f"🌟 **Message from Time Capsule AI:**\n"
    delivery_message += f"Isn't it amazing how much can change? Your {capsule.created_at.strftime('%B %Y')} self "
    delivery_message += f"wanted you to remember this moment. What do you think they'd say about where you are now?"
    
    return delivery_message

# Social Sharing Tools
SHARE_REMINDER_DESCRIPTION = TimeCapsuleToolDescription(
    description="Create shareable social media content from a reminder",
    use_when="When user wants to share a meaningful reminder or moment on social media",
    emotional_context="Creates privacy-safe, engaging content that showcases personal growth",
    side_effects="Generates platform-optimized content while protecting user privacy"
)

@mcp.tool(description=SHARE_REMINDER_DESCRIPTION.model_dump_json())
async def share_reminder(
    reminder_id: Annotated[str, Field(description="ID of the reminder to share")],
    platform: Annotated[str, Field(description="Target platform (twitter, instagram, linkedin, general)")] = "general",
    privacy_level: Annotated[str, Field(description="Privacy level (public, friends, private)")] = "public",
    user_id: Annotated[str, Field(description="User identifier")] = "default_user"
) -> str:
    """
    Create shareable content from a reminder - turn personal moments into engaging posts.
    This is what makes Time Capsule AI go viral - shareable, relatable content.
    """
    try:
        # Create shareable content
        shareable = await social_sharing.create_shareable_reminder(reminder_id, user_id, privacy_level)
        
        # Get platform-specific version
        if platform in shareable.platform_optimized:
            content = shareable.platform_optimized[platform]
        else:
            content = shareable.content
        
        # Format response
        response = f"📱 **Ready to share on {platform.title()}!**\n\n"
        response += "Here's your shareable content:\n\n"
        response += "---\n"
        response += content
        response += "\n---\n\n"
        response += f"✨ Privacy level: {privacy_level}\n"
        response += "💡 Copy and paste this to share your Time Capsule AI moment!"
        
        return response
        
    except Exception as e:
        return f"I had trouble creating shareable content from that reminder. Make sure the reminder ID is correct and try again! 📱"

SHARE_EMOTIONAL_JOURNEY_DESCRIPTION = TimeCapsuleToolDescription(
    description="Create shareable content about emotional patterns and personal growth",
    use_when="When user wants to share insights about their emotional journey or mood patterns",
    emotional_context="Creates inspiring content about personal growth and self-awareness",
    side_effects="Generates engaging social content that showcases emotional intelligence"
)

@mcp.tool(description=SHARE_EMOTIONAL_JOURNEY_DESCRIPTION.model_dump_json())
async def share_emotional_journey(
    days_back: Annotated[int, Field(description="Number of days to analyze for the journey")] = 7,
    platform: Annotated[str, Field(description="Target platform (twitter, instagram, linkedin, general)")] = "general",
    privacy_level: Annotated[str, Field(description="Privacy level (public, friends, private)")] = "public",
    user_id: Annotated[str, Field(description="User identifier")] = "default_user"
) -> str:
    """
    Create shareable content about your emotional journey and personal growth.
    This creates inspiring posts that show the power of emotional self-awareness.
    """
    try:
        # Create shareable content
        shareable = await social_sharing.create_emotional_journey_share(user_id, days_back, privacy_level)
        
        # Get platform-specific version
        if platform in shareable.platform_optimized:
            content = shareable.platform_optimized[platform]
        else:
            content = shareable.content
        
        # Format response
        response = f"📊 **Your Emotional Journey - Ready to Share!**\n\n"
        response += f"Based on your last {days_back} days:\n\n"
        response += "---\n"
        response += content
        response += "\n---\n\n"
        response += f"✨ Privacy level: {privacy_level}\n"
        response += "🌟 Share your personal growth journey and inspire others!"
        
        return response
        
    except Exception as e:
        return f"I need more emotional data to create your journey share. Keep using Time Capsule AI to build your timeline! 📊"

SHARE_TIME_CAPSULE_DESCRIPTION = TimeCapsuleToolDescription(
    description="Create shareable content from a delivered time capsule",
    use_when="When user receives a time capsule and wants to share the magical moment",
    emotional_context="Creates engaging content about rediscovering past self and personal growth",
    side_effects="Generates viral-worthy content about time capsule surprises"
)

@mcp.tool(description=SHARE_TIME_CAPSULE_DESCRIPTION.model_dump_json())
async def share_time_capsule(
    capsule_id: Annotated[str, Field(description="ID of the delivered time capsule to share")],
    platform: Annotated[str, Field(description="Target platform (twitter, instagram, linkedin, general)")] = "general",
    privacy_level: Annotated[str, Field(description="Privacy level (public, friends, private)")] = "public",
    user_id: Annotated[str, Field(description="User identifier")] = "default_user"
) -> str:
    """
    Create shareable content from a time capsule delivery - pure viral magic.
    These posts about rediscovering your past self are incredibly engaging.
    """
    try:
        # Create shareable content
        shareable = await social_sharing.create_time_capsule_share(capsule_id, user_id, privacy_level)
        
        # Get platform-specific version
        if platform in shareable.platform_optimized:
            content = shareable.platform_optimized[platform]
        else:
            content = shareable.content
        
        # Format response
        response = f"🎁 **Time Capsule Magic - Ready to Share!**\n\n"
        response += "Your surprise from past you:\n\n"
        response += "---\n"
        response += content
        response += "\n---\n\n"
        response += f"✨ Privacy level: {privacy_level}\n"
        response += "🚀 This is the kind of content that goes viral - share your time capsule magic!"
        
        return response
        
    except Exception as e:
        return f"I had trouble creating shareable content from that time capsule. Make sure it's been delivered and try again! 🎁"

SHARE_ACHIEVEMENT_DESCRIPTION = TimeCapsuleToolDescription(
    description="Create shareable content celebrating an achievement or positive moment",
    use_when="When user wants to share a proud moment or accomplishment",
    emotional_context="Creates celebratory content that highlights personal wins and positive emotions",
    side_effects="Generates uplifting social content that celebrates personal achievements"
)

@mcp.tool(description=SHARE_ACHIEVEMENT_DESCRIPTION.model_dump_json())
async def share_achievement(
    timeline_entry_id: Annotated[str, Field(description="ID of the timeline entry to celebrate")],
    platform: Annotated[str, Field(description="Target platform (twitter, instagram, linkedin, general)")] = "general",
    privacy_level: Annotated[str, Field(description="Privacy level (public, friends, private)")] = "public",
    user_id: Annotated[str, Field(description="User identifier")] = "default_user"
) -> str:
    """
    Create shareable content celebrating an achievement or positive moment.
    Perfect for sharing wins and inspiring others with your success.
    """
    try:
        # Create shareable content
        shareable = await social_sharing.create_achievement_share(timeline_entry_id, user_id, privacy_level)
        
        # Get platform-specific version
        if platform in shareable.platform_optimized:
            content = shareable.platform_optimized[platform]
        else:
            content = shareable.content
        
        # Format response
        response = f"🌟 **Achievement Celebration - Ready to Share!**\n\n"
        response += "Celebrating your win:\n\n"
        response += "---\n"
        response += content
        response += "\n---\n\n"
        response += f"✨ Privacy level: {privacy_level}\n"
        response += "🎉 Share your success and inspire others!"
        
        return response
        
    except Exception as e:
        return f"I had trouble creating shareable content from that moment. Make sure it contains positive emotions worth celebrating! 🌟"

# Run the MCP Server
async def main():
    # Initialize database
    await db_manager.initialize()
    
    # Start the automatic reminder scheduler
    await scheduler.start()
    
    print("🚀 Starting Time Capsule AI MCP Server on http://0.0.0.0:8086")
    print("💫 Ready to capture your emotional memories and deliver them back with context!")
    print("🕰️ Automatic reminder delivery is now active!")
    
    try:
        await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)
    finally:
        # Stop scheduler on shutdown
        await scheduler.stop()

if __name__ == "__main__":
    asyncio.run(main())