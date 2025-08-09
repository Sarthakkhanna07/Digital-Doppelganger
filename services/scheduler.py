"""
Automatic Reminder Scheduler for Time Capsule AI
Handles background delivery of due reminders and nudges
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Callable
import json
import aiohttp

from models import ReminderData, CompletionStatus
from services.data_manager import DataManager
from services.tone_manager import ToneManager

class ReminderScheduler:
    def __init__(self, data_manager: DataManager, tone_manager: ToneManager):
        self.data_manager = data_manager
        self.tone_manager = tone_manager
        self.is_running = False
        self.check_interval = 60  # Check every minute
        self.delivery_callbacks = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def add_delivery_callback(self, callback: Callable[[str, str], None]):
        """Add a callback function for when reminders need to be delivered"""
        self.delivery_callbacks.append(callback)
    
    async def start(self):
        """Start the background scheduler"""
        if self.is_running:
            self.logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        self.logger.info("🕰️ Starting automatic reminder scheduler...")
        
        # Start the background task
        asyncio.create_task(self._scheduler_loop())
    
    async def stop(self):
        """Stop the background scheduler"""
        self.is_running = False
        self.logger.info("⏹️ Stopping automatic reminder scheduler...")
    
    async def _scheduler_loop(self):
        """Main scheduler loop that runs in the background"""
        while self.is_running:
            try:
                await self._check_and_deliver_reminders()
                await self._check_and_deliver_nudges()
                await self._check_and_deliver_time_capsules()
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(self.check_interval)  # Continue even if there's an error
    
    async def _check_and_deliver_reminders(self):
        """Check for due reminders and deliver them"""
        try:
            # Get all users (in a real system, you'd have a user list)
            users = await self._get_active_users()
            
            for user_id in users:
                due_reminders = await self.data_manager.get_due_reminders(user_id, datetime.now())
                
                if due_reminders:
                    self.logger.info(f"📬 Found {len(due_reminders)} due reminders for user {user_id}")
                    
                    # Get user's tone profile
                    tone_profile = await self.tone_manager.build_user_profile(user_id)
                    
                    for reminder in due_reminders:
                        # Create rich contextual message
                        message = await self._create_reminder_message(reminder, tone_profile)
                        
                        # Deliver the reminder
                        await self._deliver_message(user_id, message, "reminder", reminder.id)
                        
                        # Update delivery count
                        await self.data_manager.update_reminder_delivery(reminder.id)
                        
                        self.logger.info(f"✅ Delivered reminder {reminder.id} to user {user_id}")
        
        except Exception as e:
            self.logger.error(f"Error checking reminders: {e}")
    
    async def _check_and_deliver_nudges(self):
        """Check for scheduled nudges and deliver them"""
        try:
            # Get due nudges from database
            due_nudges = await self._get_due_nudges()
            
            for nudge in due_nudges:
                user_id = nudge['user_id']
                message = nudge['trigger_message']
                
                # Deliver the nudge
                await self._deliver_message(user_id, message, "nudge", nudge['id'])
                
                # Mark as delivered
                await self._mark_nudge_delivered(nudge['id'])
                
                self.logger.info(f"🔔 Delivered nudge {nudge['id']} to user {user_id}")
        
        except Exception as e:
            self.logger.error(f"Error checking nudges: {e}")
    
    async def _check_and_deliver_time_capsules(self):
        """Check for time capsules ready for delivery"""
        try:
            users = await self._get_active_users()
            
            for user_id in users:
                # Get due time capsules
                due_capsules = await self._get_due_time_capsules(user_id)
                
                for capsule in due_capsules:
                    # Create time capsule delivery message
                    message = await self._create_time_capsule_message(capsule)
                    
                    # Deliver the time capsule
                    await self._deliver_message(user_id, message, "time_capsule", capsule['id'])
                    
                    # Mark as delivered
                    await self._mark_time_capsule_delivered(capsule['id'])
                    
                    self.logger.info(f"📦 Delivered time capsule {capsule['id']} to user {user_id}")
        
        except Exception as e:
            self.logger.error(f"Error checking time capsules: {e}")
    
    async def _create_reminder_message(self, reminder: ReminderData, tone_profile) -> str:
        """Create a rich contextual reminder message"""
        # Calculate time elapsed
        time_elapsed = datetime.now() - reminder.created_at
        time_ago = self._format_time_elapsed(time_elapsed)
        
        # Build context story
        emotion = reminder.emotional_context.primary_emotion
        activity = reminder.activity_context.primary_activity
        
        context_story = f"""🕰️ **{time_ago}**, you were {activity} and feeling {emotion} when you told me:
        
💭 "{reminder.content}"

✨ That was {time_ago} - here's your reminder with the full story of that moment! 

{self._get_encouraging_message(emotion)}"""
        
        # Adapt tone for delivery
        adapted_message = await self.tone_manager.adapt_response_tone(context_story, tone_profile)
        
        return adapted_message
    
    async def _create_time_capsule_message(self, capsule) -> str:
        """Create a time capsule delivery message"""
        created_date = datetime.fromisoformat(capsule['created_at']).strftime("%B %d, %Y")
        
        message = f"""📦 **Time Capsule Delivery!**

🗓️ **From {created_date}:**

💌 "{capsule['content']}"

✨ This is a message from your past self! What memories does this bring back?"""
        
        return message
    
    async def _deliver_message(self, user_id: str, message: str, message_type: str, item_id: str):
        """Deliver a message to the user through available channels"""
        # Call all registered delivery callbacks
        for callback in self.delivery_callbacks:
            try:
                await callback(user_id, message, message_type, item_id)
            except Exception as e:
                self.logger.error(f"Error in delivery callback: {e}")
        
        # Log the delivery
        self.logger.info(f"📤 Delivered {message_type} to user {user_id}")
    
    def _format_time_elapsed(self, delta: timedelta) -> str:
        """Format time elapsed in a human-readable way"""
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        
        if days > 0:
            return f"{days} day{'s' if days != 1 else ''} ago"
        elif hours > 0:
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif minutes > 0:
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "just now"
    
    def _get_encouraging_message(self, emotion: str) -> str:
        """Get an encouraging message based on the original emotion"""
        encouragements = {
            'stress': "You've got this! Remember, you've handled tough situations before. 💪",
            'excitement': "Hope you're still feeling that excitement! Time to make it happen! 🚀",
            'accomplishment': "You were feeling proud then - let's build on that success! 🌟",
            'tired': "Hope you're feeling more energized now! Take care of yourself. 🌱",
            'happy': "Hope that happiness is still with you! Keep that positive energy going! ☀️",
            'neutral': "Here's your reminder - you've got everything you need to succeed! ✨"
        }
        return encouragements.get(emotion, "You've got this! 💫")
    
    async def _get_active_users(self) -> List[str]:
        """Get list of active users (simplified - in real system would be more complex)"""
        try:
            # For now, get users who have recent activity
            results = await self.data_manager.db.execute_query(
                """SELECT DISTINCT user_id FROM reminders 
                   WHERE created_at > datetime('now', '-30 days')
                   UNION
                   SELECT DISTINCT user_id FROM timeline_entries 
                   WHERE timestamp > datetime('now', '-7 days')"""
            )
            return [row['user_id'] for row in results]
        except Exception:
            return ["default_user"]  # Fallback
    
    async def _get_due_nudges(self) -> List[dict]:
        """Get nudges that are due for delivery"""
        try:
            results = await self.data_manager.db.execute_query(
                """SELECT * FROM scheduled_nudges 
                   WHERE scheduled_time <= datetime('now') 
                   AND delivered = 0
                   ORDER BY scheduled_time ASC"""
            )
            return results
        except Exception:
            return []
    
    async def _get_due_time_capsules(self, user_id: str) -> List[dict]:
        """Get time capsules ready for delivery"""
        try:
            results = await self.data_manager.db.execute_query(
                """SELECT * FROM time_capsules 
                   WHERE user_id = ? 
                   AND earliest_delivery <= datetime('now')
                   AND delivered_at IS NULL
                   ORDER BY earliest_delivery ASC""",
                (user_id,)
            )
            return results
        except Exception:
            return []
    
    async def _mark_nudge_delivered(self, nudge_id: str):
        """Mark a nudge as delivered"""
        await self.data_manager.db.execute_update(
            """UPDATE scheduled_nudges 
               SET delivered = 1, delivered_at = datetime('now')
               WHERE id = ?""",
            (nudge_id,)
        )
    
    async def _mark_time_capsule_delivered(self, capsule_id: str):
        """Mark a time capsule as delivered"""
        await self.data_manager.db.execute_update(
            """UPDATE time_capsules 
               SET delivered_at = datetime('now')
               WHERE id = ?""",
            (capsule_id,)
        )

# Webhook delivery system for Puch AI integration
class PuchAIDelivery:
    def __init__(self, webhook_url: Optional[str] = None, auth_token: Optional[str] = None):
        self.webhook_url = webhook_url
        self.auth_token = auth_token
        self.logger = logging.getLogger(__name__)
    
    async def deliver_to_puch_ai(self, user_id: str, message: str, message_type: str, item_id: str):
        """Deliver message to user via Puch AI webhook"""
        if not self.webhook_url:
            self.logger.warning("No webhook URL configured for Puch AI delivery")
            return
        
        try:
            payload = {
                "user_id": user_id,
                "message": message,
                "message_type": message_type,
                "item_id": item_id,
                "timestamp": datetime.now().isoformat()
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        self.logger.info(f"✅ Successfully delivered to Puch AI: {message_type} for {user_id}")
                    else:
                        self.logger.error(f"❌ Failed to deliver to Puch AI: {response.status}")
        
        except Exception as e:
            self.logger.error(f"Error delivering to Puch AI: {e}")

# Console delivery for testing
class ConsoleDelivery:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def deliver_to_console(self, user_id: str, message: str, message_type: str, item_id: str):
        """Deliver message to console for testing"""
        print(f"\n{'='*60}")
        print(f"📬 AUTOMATIC DELIVERY - {message_type.upper()}")
        print(f"👤 User: {user_id}")
        print(f"🆔 Item: {item_id}")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        print(message)
        print(f"{'='*60}\n")
        
        self.logger.info(f"📤 Console delivery: {message_type} for {user_id}")