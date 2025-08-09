#!/usr/bin/env python3
"""
Test Automatic Reminder Delivery
Creates test reminders and shows automatic delivery in action
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up environment
os.environ["AUTH_TOKEN"] = "test_token_123"
os.environ["MY_NUMBER"] = "1234567890"
os.environ["DATABASE_URL"] = "tests/test_delivery.db"

from utils.database import DatabaseManager
from services.data_manager import DataManager
from services.tone_manager import ToneManager
from services.scheduler import ReminderScheduler, ConsoleDelivery
from services.nlp_engine import NLPEngine
from services.emotion_analyzer import EmotionAnalyzer
from models import ReminderData, CompletionStatus

class AutoDeliveryDemo:
    def __init__(self):
        self.db_manager = DatabaseManager("tests/test_delivery.db")
        self.data_manager = DataManager(self.db_manager)
        self.tone_manager = ToneManager(self.data_manager)
        self.nlp_engine = NLPEngine()
        self.emotion_analyzer = EmotionAnalyzer()
        
        # Setup scheduler
        self.scheduler = ReminderScheduler(self.data_manager, self.tone_manager)
        console_delivery = ConsoleDelivery()
        self.scheduler.add_delivery_callback(console_delivery.deliver_to_console)
    
    async def setup_demo(self):
        """Initialize database and create test data"""
        print("🚀 Setting up Automatic Delivery Demo...")
        
        # Initialize database
        await self.db_manager.initialize()
        
        # Create test user
        await self.db_manager.get_user_or_create("demo_user", "1234567890")
        
        print("✅ Database initialized")
    
    async def create_test_reminders(self):
        """Create test reminders with different due times"""
        print("\n📝 Creating test reminders...")
        
        test_cases = [
            {
                "message": "Call mom about dinner plans",
                "context": "sitting at my desk, feeling a bit stressed about work",
                "due_minutes": 1,  # Due in 1 minute
                "emotion": "stress"
            },
            {
                "message": "Submit the quarterly report",
                "context": "working late, feeling accomplished after finishing the draft",
                "due_minutes": 2,  # Due in 2 minutes
                "emotion": "accomplishment"
            },
            {
                "message": "Book dentist appointment",
                "context": "relaxing at home, feeling neutral",
                "due_minutes": 3,  # Due in 3 minutes
                "emotion": "neutral"
            }
        ]
        
        for i, case in enumerate(test_cases, 1):
            # Analyze emotion and context
            emotion_profile = await self.emotion_analyzer.analyze_emotion(
                f"{case['message']} - {case['context']}", 
                {"user_context": case['context']}
            )
            
            activity_context = await self.nlp_engine.detect_activity_context(case['context'])
            
            # Create reminder
            reminder_data = ReminderData(
                id=f"demo_reminder_{i}",
                user_id="demo_user",
                content=case['message'],
                created_at=datetime.now(),
                due_at=datetime.now() + timedelta(minutes=case['due_minutes']),
                emotional_context=emotion_profile,
                activity_context=activity_context,
                completion_status=CompletionStatus.PENDING,
                delivery_count=0
            )
            
            # Store reminder
            await self.data_manager.store_reminder(reminder_data)
            
            print(f"✅ Created reminder {i}: '{case['message']}' (due in {case['due_minutes']} minute{'s' if case['due_minutes'] != 1 else ''})")
    
    async def run_demo(self):
        """Run the automatic delivery demonstration"""
        print("\n🕰️ Starting Automatic Delivery Demo...")
        print("⏰ Reminders will be automatically delivered when due!")
        print("📺 Watch the console for automatic deliveries...")
        print("\n" + "="*60)
        
        # Start the scheduler
        await self.scheduler.start()
        
        # Run for 5 minutes to see deliveries
        demo_duration = 300  # 5 minutes
        print(f"🎬 Demo will run for {demo_duration//60} minutes...")
        print("💡 You can also manually trigger delivery checks using the MCP tool 'trigger_delivery_check'")
        
        try:
            # Keep the demo running
            await asyncio.sleep(demo_duration)
        except KeyboardInterrupt:
            print("\n⏹️ Demo stopped by user")
        finally:
            await self.scheduler.stop()
            print("\n🎉 Demo completed!")
    
    async def create_immediate_reminders(self):
        """Create reminders that are due right now for immediate testing"""
        print("📝 Creating immediate test reminders...")
        
        # Create reminders that are already due
        test_cases = [
            {
                "message": "Test immediate reminder - Call John",
                "context": "testing automatic delivery system",
                "due_minutes": -1,  # Already due (1 minute ago)
                "emotion": "excitement"
            },
            {
                "message": "Test immediate reminder - Send email",
                "context": "working on demo, feeling accomplished",
                "due_minutes": 0,  # Due right now
                "emotion": "accomplishment"
            }
        ]
        
        for i, case in enumerate(test_cases, 10):  # Start from ID 10 to avoid conflicts
            # Analyze emotion and context
            emotion_profile = await self.emotion_analyzer.analyze_emotion(
                f"{case['message']} - {case['context']}", 
                {"user_context": case['context']}
            )
            
            activity_context = await self.nlp_engine.detect_activity_context(case['context'])
            
            # Create reminder
            reminder_data = ReminderData(
                id=f"immediate_reminder_{i}",
                user_id="demo_user",
                content=case['message'],
                created_at=datetime.now() - timedelta(minutes=5),  # Created 5 minutes ago
                due_at=datetime.now() + timedelta(minutes=case['due_minutes']),
                emotional_context=emotion_profile,
                activity_context=activity_context,
                completion_status=CompletionStatus.PENDING,
                delivery_count=0
            )
            
            # Store reminder
            await self.data_manager.store_reminder(reminder_data)
            
            print(f"✅ Created immediate reminder {i}: '{case['message']}'")

    async def manual_trigger_test(self):
        """Test manual triggering of delivery checks"""
        print("\n🔧 Testing manual delivery trigger...")
        
        # Force a delivery check
        await self.scheduler._check_and_deliver_reminders()
        await self.scheduler._check_and_deliver_nudges()
        await self.scheduler._check_and_deliver_time_capsules()
        
        print("✅ Manual trigger completed!")
    
    async def cleanup(self):
        """Clean up test database"""
        if os.path.exists("tests/test_delivery.db"):
            os.remove("tests/test_delivery.db")
            print("🧹 Cleaned up test database")

async def main():
    """Run the automatic delivery demonstration"""
    demo = AutoDeliveryDemo()
    
    try:
        # Setup
        await demo.setup_demo()
        
        # Create test reminders
        await demo.create_test_reminders()
        
        # Show what we created
        print(f"\n📊 Demo Status:")
        print(f"⏰ Current time: {datetime.now().strftime('%H:%M:%S')}")
        print(f"📬 3 reminders created with staggered delivery times")
        print(f"🔄 Scheduler will check every 60 seconds")
        
        # Ask user what they want to do
        print(f"\n🎯 Choose demo mode:")
        print(f"1. Run automatic demo (5 minutes)")
        print(f"2. Manual trigger test (immediate)")
        print(f"3. Both")
        
        choice = input("Enter choice (1-3): ").strip()
        
        if choice in ["1", "3"]:
            await demo.run_demo()
        
        if choice in ["2", "3"]:
            print("\n⚡ Creating immediate reminders for testing...")
            await demo.create_immediate_reminders()
            await demo.manual_trigger_test()
        
        if choice not in ["1", "2", "3"]:
            print("Invalid choice, running manual test...")
            print("\n⚡ Creating immediate reminders for testing...")
            await demo.create_immediate_reminders()
            await demo.manual_trigger_test()
    
    except Exception as e:
        print(f"❌ Demo error: {e}")
    
    finally:
        await demo.cleanup()

if __name__ == "__main__":
    print("🕰️ Time Capsule AI - Automatic Delivery Demo")
    print("=" * 50)
    asyncio.run(main())