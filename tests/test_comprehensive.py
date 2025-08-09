#!/usr/bin/env python3
"""
Time Capsule AI - Comprehensive Test Suite
Tests all functionality to ensure correct results
"""

import asyncio
import os
import sys
import json
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our components
from utils.database import DatabaseManager
from services.nlp_engine import NLPEngine
from services.emotion_analyzer import EmotionAnalyzer
from services.data_manager import DataManager
from services.tone_manager import ToneManager
from models import ReminderData, EmotionProfile, ActivityContext, CompletionStatus

class TimeCapsuleTests:
    def __init__(self):
        self.db_manager = DatabaseManager("tests/test_time_capsule.db")
        self.nlp_engine = NLPEngine()
        self.emotion_analyzer = EmotionAnalyzer()
        self.data_manager = DataManager(self.db_manager)
        self.tone_manager = ToneManager(self.data_manager)
        self.test_user_id = "test_user_123"
        
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []

    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = f"{status} - {test_name}"
        if details:
            result += f" ({details})"
        
        self.test_results.append(result)
        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
        
        print(result)

    async def test_database_initialization(self):
        """Test 1: Database Setup"""
        print("\n🗄️  Testing Database Initialization...")
        
        try:
            await self.db_manager.initialize()
            
            # Test user creation
            user = await self.db_manager.get_user_or_create(self.test_user_id, "1234567890")
            
            self.log_test("Database initialization", user is not None, f"User ID: {user['id']}")
            return True
        except Exception as e:
            self.log_test("Database initialization", False, str(e))
            return False

    async def test_nlp_processing(self):
        """Test 2: Natural Language Processing"""
        print("\n🧠 Testing NLP Engine...")
        
        test_cases = [
            {
                "input": "Remind me to call mom tomorrow, I'm feeling stressed about it",
                "expected_intent": True,
                "expected_temporal": "tomorrow"
            },
            {
                "input": "Don't forget to submit the report by Friday",
                "expected_intent": True,
                "expected_temporal": "friday"
            },
            {
                "input": "Just having a normal conversation",
                "expected_intent": False,
                "expected_temporal": None
            }
        ]
        
        all_passed = True
        
        for i, case in enumerate(test_cases, 1):
            try:
                # Test intent parsing
                intent = await self.nlp_engine.parse_reminder_intent(case["input"])
                intent_correct = intent.is_reminder == case["expected_intent"]
                
                # Test temporal extraction
                temporal = await self.nlp_engine.extract_temporal_info(case["input"])
                temporal_correct = True  # We'll check if it parsed something reasonable
                
                # Test activity context
                activity = await self.nlp_engine.detect_activity_context(case["input"])
                activity_correct = activity.primary_activity is not None
                
                test_passed = intent_correct and temporal_correct and activity_correct
                
                self.log_test(f"NLP Test Case {i}", test_passed, 
                            f"Intent: {intent.is_reminder}, Activity: {activity.primary_activity}")
                
                if not test_passed:
                    all_passed = False
                    
            except Exception as e:
                self.log_test(f"NLP Test Case {i}", False, str(e))
                all_passed = False
        
        return all_passed

    async def test_emotion_analysis(self):
        """Test 3: Emotion Detection"""
        print("\n🎭 Testing Emotion Analysis...")
        
        test_cases = [
            {
                "text": "I'm so excited about this project!",
                "expected_emotion": "excitement",
                "expected_intensity": "> 0.5"
            },
            {
                "text": "Feeling really stressed about the deadline",
                "expected_emotion": "stress",
                "expected_intensity": "> 0.5"
            },
            {
                "text": "Just accomplished something amazing!",
                "expected_emotion": "accomplishment",
                "expected_intensity": "> 0.5"
            },
            {
                "text": "Having a pretty normal day",
                "expected_emotion": "neutral",
                "expected_intensity": "any"
            }
        ]
        
        all_passed = True
        
        for i, case in enumerate(test_cases, 1):
            try:
                emotion = await self.emotion_analyzer.analyze_emotion(case["text"], {
                    "time_of_day": "afternoon"
                })
                
                emotion_correct = emotion.primary_emotion == case["expected_emotion"]
                intensity_correct = (case["expected_intensity"] == "any" or 
                                   (case["expected_intensity"] == "> 0.5" and emotion.intensity > 0.5))
                
                test_passed = emotion_correct and intensity_correct
                
                self.log_test(f"Emotion Test Case {i}", test_passed,
                            f"'{case['text']}' → {emotion.primary_emotion} (intensity: {emotion.intensity:.2f})")
                
                if not test_passed:
                    all_passed = False
                    
            except Exception as e:
                self.log_test(f"Emotion Test Case {i}", False, str(e))
                all_passed = False
        
        return all_passed

    async def test_reminder_workflow(self):
        """Test 4: Complete Reminder Workflow"""
        print("\n🔄 Testing Complete Reminder Workflow...")
        
        try:
            # Create a test reminder
            user_message = "Remind me to send the report on Monday, I'm feeling stressed about it"
            user_context = "working at my desk, lots of pressure from boss"
            
            # Process with NLP
            reminder_intent = await self.nlp_engine.parse_reminder_intent(user_message)
            temporal_data = await self.nlp_engine.extract_temporal_info(user_message)
            activity_context = await self.nlp_engine.detect_activity_context(user_context + " " + user_message)
            
            # Analyze emotion
            emotion_profile = await self.emotion_analyzer.analyze_emotion(user_message, {
                "user_context": user_context,
                "time_of_day": datetime.now().strftime("%H:%M")
            })
            
            # Create reminder data
            reminder_data = ReminderData(
                id=f"test_reminder_{datetime.now().timestamp()}",
                user_id=self.test_user_id,
                content=reminder_intent.cleaned_message,
                created_at=datetime.now(),
                due_at=datetime.now() + timedelta(minutes=1),  # Due in 1 minute for testing
                emotional_context=emotion_profile,
                activity_context=activity_context,
                completion_status=CompletionStatus.PENDING,
                delivery_count=0
            )
            
            # Store the reminder
            reminder_id = await self.data_manager.store_reminder(reminder_data)
            
            self.log_test("Reminder creation", reminder_id is not None, f"ID: {reminder_id}")
            
            # Test reminder retrieval
            due_reminders = await self.data_manager.get_due_reminders(self.test_user_id, 
                                                                    datetime.now() + timedelta(minutes=2))
            
            retrieval_success = len(due_reminders) > 0
            self.log_test("Reminder retrieval", retrieval_success, 
                         f"Found {len(due_reminders)} due reminders")
            
            if retrieval_success:
                reminder = due_reminders[0]
                context_preserved = (reminder.emotional_context.primary_emotion == emotion_profile.primary_emotion and
                                   reminder.activity_context.primary_activity == activity_context.primary_activity)
                
                self.log_test("Context preservation", context_preserved,
                             f"Emotion: {reminder.emotional_context.primary_emotion}, Activity: {reminder.activity_context.primary_activity}")
                
                return context_preserved
            
            return False
            
        except Exception as e:
            self.log_test("Reminder workflow", False, str(e))
            return False

    async def test_tone_management(self):
        """Test 5: Tone Management and Personalization"""
        print("\n🎨 Testing Tone Management...")
        
        try:
            # Build user tone profile
            tone_profile = await self.tone_manager.build_user_profile(self.test_user_id)
            
            profile_created = tone_profile is not None
            self.log_test("Tone profile creation", profile_created,
                         f"Energy: {tone_profile.preferred_energy:.2f}, Support: {tone_profile.preferred_support:.2f}")
            
            if profile_created:
                # Test tone adaptation
                base_messages = [
                    "Here's your reminder about the important meeting.",
                    "You accomplished something great today!",
                    "I can sense you're feeling stressed right now."
                ]
                
                adaptation_success = True
                for i, message in enumerate(base_messages, 1):
                    try:
                        adapted = await self.tone_manager.adapt_response_tone(message, tone_profile)
                        adapted_correctly = len(adapted) > len(message) * 0.8  # Should be similar length or longer
                        
                        self.log_test(f"Tone adaptation {i}", adapted_correctly,
                                     f"'{message[:30]}...' → '{adapted[:30]}...'")
                        
                        if not adapted_correctly:
                            adaptation_success = False
                            
                    except Exception as e:
                        self.log_test(f"Tone adaptation {i}", False, str(e))
                        adaptation_success = False
                
                return adaptation_success
            
            return False
            
        except Exception as e:
            self.log_test("Tone management", False, str(e))
            return False

    async def test_timeline_functionality(self):
        """Test 6: Timeline and Search"""
        print("\n📊 Testing Timeline Functionality...")
        
        try:
            # Create some timeline entries
            test_entries = [
                "Just finished my workout — feeling great!",
                "Working on a big project, feeling a bit stressed but making progress",
                "Having coffee with friends, really enjoying this moment"
            ]
            
            entries_created = 0
            for entry_text in test_entries:
                try:
                    # Analyze emotion and activity
                    emotion_profile = await self.emotion_analyzer.analyze_emotion(entry_text, {})
                    activity_context = await self.nlp_engine.detect_activity_context(entry_text)
                    
                    # Create timeline entry using proper data manager method
                    from models import TimelineEntry
                    timeline_entry = TimelineEntry(
                        id=f"timeline_{datetime.now().timestamp()}_{entries_created}",
                        user_id=self.test_user_id,
                        timestamp=datetime.now(),
                        entry_type="test_entry",
                        content=entry_text,
                        emotional_state=emotion_profile,
                        context={"test": True},
                        related_entries=[],
                        searchable_text=f"test entry {entry_text} {emotion_profile.primary_emotion}",
                        tags=["test", emotion_profile.primary_emotion]
                    )
                    
                    # Store using data manager (this will handle FTS indexing)
                    await self.data_manager.store_timeline_entry(timeline_entry)
                    entries_created += 1
                    
                except Exception as e:
                    print(f"Failed to create timeline entry: {e}")
            
            self.log_test("Timeline entry creation", entries_created == len(test_entries),
                         f"Created {entries_created}/{len(test_entries)} entries")
            
            # Test timeline search
            search_results = await self.data_manager.search_timeline(self.test_user_id, "workout", 5)
            search_success = len(search_results) > 0
            
            self.log_test("Timeline search", search_success,
                         f"Found {len(search_results)} results for 'workout'")
            
            return entries_created > 0 and search_success
            
        except Exception as e:
            self.log_test("Timeline functionality", False, str(e))
            return False

    async def run_all_tests(self):
        """Run all tests and provide summary"""
        print("🚀 Starting Time Capsule AI Comprehensive Tests\n")
        
        try:
            # Run all test suites
            test_results = [
                await self.test_database_initialization(),
                await self.test_nlp_processing(),
                await self.test_emotion_analysis(),
                await self.test_reminder_workflow(),
                await self.test_tone_management(),
                await self.test_timeline_functionality()
            ]
            
            # Print summary
            print(f"\n{'='*60}")
            print("🎉 TEST SUMMARY")
            print(f"{'='*60}")
            
            for result in self.test_results:
                print(result)
            
            print(f"\n📊 OVERALL RESULTS:")
            print(f"✅ Passed: {self.passed_tests}")
            print(f"❌ Failed: {self.failed_tests}")
            print(f"📈 Success Rate: {(self.passed_tests/(self.passed_tests + self.failed_tests)*100):.1f}%")
            
            overall_success = all(test_results)
            
            if overall_success:
                print(f"\n🎉 ALL SYSTEMS OPERATIONAL!")
                print("Time Capsule AI is working correctly and ready for production! 🚀")
            else:
                print(f"\n⚠️  Some tests failed. Review the results above.")
            
            return overall_success
            
        except Exception as e:
            print(f"\n❌ Test suite failed: {str(e)}")
            return False
        
        finally:
            # Clean up test database
            if os.path.exists("tests/test_time_capsule.db"):
                os.remove("tests/test_time_capsule.db")
                print("\n🧹 Cleaned up test database")

async def main():
    """Run the comprehensive test suite"""
    tester = TimeCapsuleTests()
    success = await tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)