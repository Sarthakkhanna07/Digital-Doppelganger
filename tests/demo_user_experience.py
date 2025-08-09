#!/usr/bin/env python3
"""
Demo: User Experience with Automatic Reminders
Shows exactly what users will receive when reminders are due
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up environment
os.environ["AUTH_TOKEN"] = "demo_token"
os.environ["MY_NUMBER"] = "1234567890"
os.environ["DATABASE_URL"] = "tests/demo_user_experience.db"

from utils.database import DatabaseManager
from services.data_manager import DataManager
from services.tone_manager import ToneManager
from services.scheduler import ReminderScheduler
from services.nlp_engine import NLPEngine
from services.emotion_analyzer import EmotionAnalyzer
from models import ReminderData, CompletionStatus

class UserExperienceDemo:
    def __init__(self):
        self.db_manager = DatabaseManager("tests/demo_user_experience.db")
        self.data_manager = DataManager(self.db_manager)
        self.tone_manager = ToneManager(self.data_manager)
        self.nlp_engine = NLPEngine()
        self.emotion_analyzer = EmotionAnalyzer()
        
        # Setup scheduler with custom delivery
        self.scheduler = ReminderScheduler(self.data_manager, self.tone_manager)
        self.scheduler.add_delivery_callback(self.simulate_user_notification)
    
    async def simulate_user_notification(self, user_id: str, message: str, message_type: str, item_id: str):
        """Simulate what the user would receive on their phone/WhatsApp"""
        print(f"\n" + "="*60)
        print(f"📱 USER'S PHONE - WhatsApp Message from Time Capsule AI")
        print(f"="*60)
        print(f"👤 To: {user_id}")
        print(f"⏰ {datetime.now().strftime('%I:%M %p')}")
        print(f"-" * 60)
        print(message)
        print(f"="*60)
        print(f"💬 [User can reply to this message]")
        print(f"🔄 [This was delivered automatically - no manual action needed]")
        print(f"="*60 + "\n")
    
    async def setup_demo(self):
        """Setup the demo environment"""
        print("🚀 Setting up User Experience Demo...")
        await self.db_manager.initialize()
        await self.db_manager.get_user_or_create("john_doe", "1234567890")
        print("✅ Demo environment ready")
    
    async def create_realistic_reminders(self):
        """Create realistic reminders that users would actually set"""
        print("\n📝 Creating realistic user reminders...")
        
        realistic_scenarios = [
            {
                "user_message": "Remind me to call mom about dinner plans tomorrow",
                "user_context": "sitting at my desk after work, feeling a bit stressed about coordinating family stuff",
                "due_minutes": 0,  # Due now for demo
                "scenario": "Family coordination while stressed at work"
            },
            {
                "user_message": "Don't forget to submit the quarterly report by Friday",
                "user_context": "working late, just finished the draft and feeling accomplished",
                "due_minutes": 0,  # Due now for demo  
                "scenario": "Work deadline with sense of accomplishment"
            },
            {
                "user_message": "Remind me to book that dentist appointment",
                "user_context": "relaxing at home on Sunday, feeling neutral but motivated to get things done",
                "due_minutes": 0,  # Due now for demo
                "scenario": "Personal task while relaxed and motivated"
            }
        ]
        
        for i, scenario in enumerate(realistic_scenarios, 1):
            print(f"\n🎭 Scenario {i}: {scenario['scenario']}")
            print(f"👤 User says: \"{scenario['user_message']}\"")
            print(f"📍 Context: {scenario['user_context']}")
            
            # Process like the real system would
            emotion_profile = await self.emotion_analyzer.analyze_emotion(
                scenario['user_message'] + " " + scenario['user_context'],
                {"user_context": scenario['user_context']}
            )
            
            activity_context = await self.nlp_engine.detect_activity_context(scenario['user_context'])
            
            # Create reminder (set created_at to past for realistic time elapsed)
            reminder_data = ReminderData(
                id=f"user_reminder_{i}",
                user_id="john_doe",
                content=scenario['user_message'].replace("Remind me to ", "").replace("Don't forget to ", ""),
                created_at=datetime.now() - timedelta(hours=24),  # Created yesterday
                due_at=datetime.now() + timedelta(minutes=scenario['due_minutes']),
                emotional_context=emotion_profile,
                activity_context=activity_context,
                completion_status=CompletionStatus.PENDING,
                delivery_count=0
            )
            
            await self.data_manager.store_reminder(reminder_data)
            print(f"✅ Reminder stored with emotional context: {emotion_profile.primary_emotion}")
    
    async def demonstrate_automatic_delivery(self):
        """Show what happens when reminders are automatically delivered"""
        print(f"\n🕰️ AUTOMATIC DELIVERY DEMONSTRATION")
        print(f"⏰ Current time: {datetime.now().strftime('%I:%M %p on %B %d, %Y')}")
        print(f"🤖 Time Capsule AI is now checking for due reminders...")
        print(f"📡 This happens automatically every 60 seconds in the background")
        
        # Trigger the automatic delivery
        await self.scheduler._check_and_deliver_reminders()
        
        print(f"\n✨ This is exactly what users experience:")
        print(f"   • No manual checking needed")
        print(f"   • Reminders arrive automatically when due")
        print(f"   • Full emotional context is preserved")
        print(f"   • Personalized tone based on user preferences")
        print(f"   • Rich storytelling recreates the original moment")
    
    async def show_user_interaction_flow(self):
        """Show the complete user interaction flow"""
        print(f"\n" + "="*80)
        print(f"🎬 COMPLETE USER EXPERIENCE FLOW")
        print(f"="*80)
        
        print(f"\n📅 YESTERDAY:")
        print(f"👤 User (stressed at work): \"Remind me to call mom about dinner plans tomorrow\"")
        print(f"🤖 Time Capsule AI: \"Got it! I'll remind you tomorrow with the full context of how you're feeling right now.\"")
        print(f"💾 System: Stores reminder with emotional context (stress, work environment)")
        
        print(f"\n🕰️ TODAY (24 hours later):")
        print(f"🤖 Background Scheduler: *Automatically checks for due reminders*")
        print(f"📬 System: *Finds due reminder and prepares delivery*")
        print(f"📱 User receives automatic WhatsApp message (shown above)")
        
        print(f"\n💬 USER CAN RESPOND:")
        print(f"👤 \"Thanks! I'll call her now\"")
        print(f"👤 \"Snooze for 2 hours\"")
        print(f"👤 \"Mark as done\"")
        
        print(f"\n🔄 SYSTEM CONTINUES:")
        print(f"📊 Learns from user response")
        print(f"🎯 Improves future reminder timing and tone")
        print(f"📈 Builds user's personal timeline")
        
        print(f"="*80)
    
    async def cleanup(self):
        """Clean up demo database"""
        if os.path.exists("tests/demo_user_experience.db"):
            os.remove("tests/demo_user_experience.db")
            print("🧹 Demo cleanup completed")

async def main():
    """Run the user experience demonstration"""
    demo = UserExperienceDemo()
    
    try:
        print("🕰️ Time Capsule AI - User Experience Demo")
        print("=" * 50)
        print("This shows exactly what users will experience with automatic reminders")
        
        await demo.setup_demo()
        await demo.create_realistic_reminders()
        await demo.demonstrate_automatic_delivery()
        await demo.show_user_interaction_flow()
        
        print(f"\n🎉 Demo completed!")
        print(f"💡 In production, users get these messages automatically in WhatsApp")
        print(f"🚀 No manual intervention needed - it's fully automatic!")
        
    except Exception as e:
        print(f"❌ Demo error: {e}")
    
    finally:
        await demo.cleanup()

if __name__ == "__main__":
    asyncio.run(main())