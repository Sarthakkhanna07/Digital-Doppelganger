"""
Social Sharing Service for Time Capsule AI
Creates shareable content from reminders and moments
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import re

from models import ReminderData, TimelineEntry, ShareableContent, EmotionProfile

class SocialSharingManager:
    def __init__(self, data_manager):
        self.data_manager = data_manager
        
        # Templates for different types of shareable content
        self.share_templates = {
            'reminder_story': [
                "Past me left future me the perfect reminder 💭\n\n\"{content}\"\n\n{time_context}\n\n#TimeCapsuleAI #RemindersWithSoul",
                "When your AI remembers not just WHAT but HOW you felt ✨\n\n\"{content}\"\n\n{time_context}\n\n#EmotionalAI #PersonalGrowth",
                "This is why I love my AI assistant - it captures the whole story 🎭\n\n\"{content}\"\n\n{time_context}\n\n#AIThatCares #MemoryKeeper"
            ],
            'emotional_journey': [
                "My emotional journey this week 🎢\n\n{emotion_summary}\n\nIt's amazing to see patterns when you track your feelings!\n\n#EmotionalIntelligence #SelfAwareness",
                "Tracking my moods with AI and the insights are incredible 📊\n\n{emotion_summary}\n\n#MoodTracking #PersonalGrowth #AIInsights",
                "My AI helped me realize something about my emotional patterns 🧠\n\n{emotion_summary}\n\n#SelfDiscovery #EmotionalAI"
            ],
            'time_capsule_reveal': [
                "My past self just surprised me with this time capsule 🎁\n\n\"{content}\"\n\n{time_context}\n\nIt's like getting a letter from another version of yourself!\n\n#TimeCapsule #PastSelf",
                "Time capsule from {months_ago} months ago just opened ✨\n\n\"{content}\"\n\n{reflection}\n\n#PersonalGrowth #TimeTravel #Memories",
                "My AI saved this moment for me to rediscover 💫\n\n\"{content}\"\n\n{time_context}\n\n#AIMemories #Rediscovery"
            ],
            'achievement_celebration': [
                "Celebrating this win! 🎉\n\n\"{content}\"\n\n{emotion_context}\n\n#Achievement #PersonalWin #Grateful",
                "My AI captured this proud moment 🌟\n\n\"{content}\"\n\n{emotion_context}\n\n#ProudMoment #Success #AISupport",
                "Sometimes you need to celebrate the small wins too ✨\n\n\"{content}\"\n\n{emotion_context}\n\n#SmallWins #Progress"
            ],
            'wisdom_share': [
                "Insight from my personal AI assistant 💡\n\n{insight}\n\n{context}\n\n#AIWisdom #PersonalGrowth #Insights",
                "My emotional AI just helped me realize something 🧠\n\n{insight}\n\n{context}\n\n#SelfAwareness #EmotionalIntelligence",
                "This is why I love having an AI that understands me 💭\n\n{insight}\n\n{context}\n\n#PersonalAI #Understanding"
            ]
        }
        
        # Privacy filters to remove sensitive information
        self.privacy_filters = [
            # Remove specific names (keep first name only)
            (r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', lambda m: m.group().split()[0] + " [name]"),
            # Remove phone numbers
            (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', "[phone]"),
            # Remove email addresses
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "[email]"),
            # Remove specific addresses
            (r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)\b', "[address]"),
            # Remove specific dollar amounts over $100
            (r'\$\d{3,}(?:,\d{3})*(?:\.\d{2})?', "$[amount]"),
            # Remove specific company names (common patterns)
            (r'\b[A-Z][a-z]+\s+(?:Inc|LLC|Corp|Corporation|Company|Co)\b', "[company]")
        ]
        
        # Emoji mappings for emotions
        self.emotion_emojis = {
            'joy': '😊', 'happiness': '😊', 'excited': '🤩', 'excitement': '🤩',
            'accomplishment': '🌟', 'proud': '🌟', 'satisfied': '✨',
            'stress': '😤', 'overwhelmed': '😰', 'anxiety': '😟',
            'calm': '😌', 'peaceful': '🕊️', 'content': '😊',
            'sad': '😔', 'disappointed': '😞', 'down': '😔',
            'angry': '😠', 'frustrated': '😤', 'annoyed': '😒',
            'surprised': '😲', 'amazed': '🤩', 'shocked': '😱',
            'tired': '😴', 'exhausted': '😵', 'drained': '😪',
            'motivated': '💪', 'determined': '💪', 'focused': '🎯',
            'grateful': '🙏', 'thankful': '🙏', 'blessed': '🙏',
            'confused': '🤔', 'uncertain': '🤷', 'curious': '🤔',
            'neutral': '😐', 'okay': '👍', 'fine': '👌'
        }
    
    async def create_shareable_reminder(self, reminder_id: str, user_id: str, 
                                      privacy_level: str = "public") -> ShareableContent:
        """Create shareable content from a reminder"""
        try:
            # Get the reminder
            reminder = await self._get_reminder_by_id(reminder_id, user_id)
            if not reminder:
                raise Exception("Reminder not found")
            
            # Apply privacy filters
            safe_content = self._apply_privacy_filters(reminder.content, privacy_level)
            
            # Calculate time context
            time_elapsed = datetime.now() - reminder.created_at
            time_context = self._build_time_context(reminder, time_elapsed)
            
            # Select template
            template = random.choice(self.share_templates['reminder_story'])
            
            # Generate content
            share_text = template.format(
                content=safe_content,
                time_context=time_context
            )
            
            # Create platform-optimized versions
            platform_versions = {
                'twitter': self._optimize_for_twitter(share_text),
                'instagram': self._optimize_for_instagram(share_text),
                'linkedin': self._optimize_for_linkedin(share_text),
                'general': share_text
            }
            
            return ShareableContent(
                content_type="text",
                content=share_text,
                privacy_level=privacy_level,
                platform_optimized=platform_versions
            )
            
        except Exception as e:
            raise Exception(f"Failed to create shareable reminder: {str(e)}")
    
    async def create_emotional_journey_share(self, user_id: str, days_back: int = 7,
                                           privacy_level: str = "public") -> ShareableContent:
        """Create shareable content about emotional journey"""
        try:
            # Get timeline entries
            timeline_entries = await self.data_manager.get_user_timeline(user_id, days_back)
            
            if len(timeline_entries) < 3:
                raise Exception("Not enough data for emotional journey")
            
            # Analyze emotional patterns
            emotions = [entry.emotional_state.primary_emotion for entry in timeline_entries]
            emotion_summary = self._create_emotion_summary(emotions, days_back)
            
            # Select template
            template = random.choice(self.share_templates['emotional_journey'])
            
            # Generate content
            share_text = template.format(emotion_summary=emotion_summary)
            
            # Create platform-optimized versions
            platform_versions = {
                'twitter': self._optimize_for_twitter(share_text),
                'instagram': self._optimize_for_instagram(share_text),
                'linkedin': self._optimize_for_linkedin(share_text),
                'general': share_text
            }
            
            return ShareableContent(
                content_type="text",
                content=share_text,
                privacy_level=privacy_level,
                platform_optimized=platform_versions
            )
            
        except Exception as e:
            raise Exception(f"Failed to create emotional journey share: {str(e)}")
    
    async def create_time_capsule_share(self, capsule_id: str, user_id: str,
                                      privacy_level: str = "public") -> ShareableContent:
        """Create shareable content from a delivered time capsule"""
        try:
            # Get the time capsule
            capsule = await self._get_time_capsule_by_id(capsule_id, user_id)
            if not capsule:
                raise Exception("Time capsule not found")
            
            # Apply privacy filters
            safe_content = self._apply_privacy_filters(capsule.content, privacy_level)
            
            # Calculate time context
            time_elapsed = datetime.now() - capsule.created_at
            months_ago = max(1, time_elapsed.days // 30)
            
            # Build reflection
            reflection = self._build_capsule_reflection(capsule, time_elapsed)
            time_context = f"From {months_ago} months ago when I was feeling {capsule.emotional_snapshot.primary_emotion}"
            
            # Select template
            template = random.choice(self.share_templates['time_capsule_reveal'])
            
            # Generate content
            share_text = template.format(
                content=safe_content,
                months_ago=months_ago,
                time_context=time_context,
                reflection=reflection
            )
            
            # Create platform-optimized versions
            platform_versions = {
                'twitter': self._optimize_for_twitter(share_text),
                'instagram': self._optimize_for_instagram(share_text),
                'linkedin': self._optimize_for_linkedin(share_text),
                'general': share_text
            }
            
            return ShareableContent(
                content_type="text",
                content=share_text,
                privacy_level=privacy_level,
                platform_optimized=platform_versions
            )
            
        except Exception as e:
            raise Exception(f"Failed to create time capsule share: {str(e)}")
    
    async def create_achievement_share(self, timeline_entry_id: str, user_id: str,
                                     privacy_level: str = "public") -> ShareableContent:
        """Create shareable content celebrating an achievement"""
        try:
            # Get the timeline entry
            entry = await self._get_timeline_entry_by_id(timeline_entry_id, user_id)
            if not entry:
                raise Exception("Timeline entry not found")
            
            # Check if it's achievement-worthy
            if entry.emotional_state.primary_emotion not in ['accomplishment', 'joy', 'excited', 'proud']:
                raise Exception("Entry doesn't contain achievement emotions")
            
            # Apply privacy filters
            safe_content = self._apply_privacy_filters(entry.content, privacy_level)
            
            # Build emotion context
            emotion_emoji = self.emotion_emojis.get(entry.emotional_state.primary_emotion, '✨')
            emotion_context = f"Feeling {entry.emotional_state.primary_emotion} {emotion_emoji}"
            
            # Select template
            template = random.choice(self.share_templates['achievement_celebration'])
            
            # Generate content
            share_text = template.format(
                content=safe_content,
                emotion_context=emotion_context
            )
            
            # Create platform-optimized versions
            platform_versions = {
                'twitter': self._optimize_for_twitter(share_text),
                'instagram': self._optimize_for_instagram(share_text),
                'linkedin': self._optimize_for_linkedin(share_text),
                'general': share_text
            }
            
            return ShareableContent(
                content_type="text",
                content=share_text,
                privacy_level=privacy_level,
                platform_optimized=platform_versions
            )
            
        except Exception as e:
            raise Exception(f"Failed to create achievement share: {str(e)}")
    
    def _apply_privacy_filters(self, content: str, privacy_level: str) -> str:
        """Apply privacy filters based on privacy level"""
        if privacy_level == "private":
            return content  # No filtering for private shares
        
        filtered_content = content
        
        # Apply all privacy filters
        for pattern, replacement in self.privacy_filters:
            if callable(replacement):
                filtered_content = re.sub(pattern, replacement, filtered_content)
            else:
                filtered_content = re.sub(pattern, replacement, filtered_content)
        
        return filtered_content
    
    def _build_time_context(self, reminder: ReminderData, time_elapsed: timedelta) -> str:
        """Build time context description"""
        days = time_elapsed.days
        emotion = reminder.emotional_context.primary_emotion
        emotion_emoji = self.emotion_emojis.get(emotion, '💭')
        
        if days == 0:
            return f"Created today while feeling {emotion} {emotion_emoji}"
        elif days == 1:
            return f"Created yesterday while feeling {emotion} {emotion_emoji}"
        elif days < 7:
            return f"Created {days} days ago while feeling {emotion} {emotion_emoji}"
        elif days < 30:
            weeks = days // 7
            return f"Created {weeks} week{'s' if weeks != 1 else ''} ago while feeling {emotion} {emotion_emoji}"
        else:
            months = days // 30
            return f"Created {months} month{'s' if months != 1 else ''} ago while feeling {emotion} {emotion_emoji}"
    
    def _create_emotion_summary(self, emotions: List[str], days: int) -> str:
        """Create a summary of emotional patterns"""
        if not emotions:
            return "Not enough emotional data to analyze"
        
        # Count emotions
        emotion_counts = {}
        for emotion in emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        # Get top emotions
        top_emotions = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Build summary
        summary_parts = []
        for emotion, count in top_emotions:
            emoji = self.emotion_emojis.get(emotion, '💭')
            percentage = (count / len(emotions)) * 100
            summary_parts.append(f"{emotion.title()} {emoji} {percentage:.0f}%")
        
        return f"Past {days} days: " + " • ".join(summary_parts)
    
    def _build_capsule_reflection(self, capsule, time_elapsed: timedelta) -> str:
        """Build reflection text for time capsule"""
        months = max(1, time_elapsed.days // 30)
        emotion_then = capsule.emotional_snapshot.primary_emotion
        
        reflections = [
            f"Crazy how much can change in {months} months!",
            f"Past me was feeling {emotion_then} - what a journey since then!",
            f"It's like getting advice from a different version of myself",
            f"Amazing to see how my perspective has evolved",
            f"This hits different now than it would have {months} months ago"
        ]
        
        return random.choice(reflections)
    
    def _optimize_for_twitter(self, content: str) -> str:
        """Optimize content for Twitter's character limit"""
        if len(content) <= 280:
            return content
        
        # Truncate and add ellipsis
        truncated = content[:270] + "... 🧵"
        return truncated
    
    def _optimize_for_instagram(self, content: str) -> str:
        """Optimize content for Instagram"""
        # Instagram allows longer content, but add more emojis and line breaks
        optimized = content.replace('. ', '.\n\n')
        
        # Add more visual elements
        if '✨' not in optimized:
            optimized = '✨ ' + optimized + ' ✨'
        
        return optimized
    
    def _optimize_for_linkedin(self, content: str) -> str:
        """Optimize content for LinkedIn's professional tone"""
        # Make it more professional
        professional_content = content.replace('#TimeCapsuleAI', '#PersonalDevelopment #AI')
        professional_content = professional_content.replace('#EmotionalAI', '#ArtificialIntelligence #PersonalGrowth')
        
        # Add professional context
        if 'AI' in professional_content:
            professional_content += '\n\nThoughts on how AI can support personal development?'
        
        return professional_content
    
    async def _get_reminder_by_id(self, reminder_id: str, user_id: str) -> Optional[ReminderData]:
        """Get reminder by ID"""
        try:
            results = await self.data_manager.db.execute_query(
                "SELECT * FROM reminders WHERE id = ? AND user_id = ?",
                (reminder_id, user_id)
            )
            
            if results:
                return self.data_manager._row_to_reminder(results[0])
            return None
            
        except Exception:
            return None
    
    async def _get_time_capsule_by_id(self, capsule_id: str, user_id: str):
        """Get time capsule by ID"""
        try:
            results = await self.data_manager.db.execute_query(
                "SELECT * FROM time_capsules WHERE id = ? AND user_id = ?",
                (capsule_id, user_id)
            )
            
            if results:
                return self.data_manager._row_to_time_capsule(results[0])
            return None
            
        except Exception:
            return None
    
    async def _get_timeline_entry_by_id(self, entry_id: str, user_id: str) -> Optional[TimelineEntry]:
        """Get timeline entry by ID"""
        try:
            results = await self.data_manager.db.execute_query(
                "SELECT * FROM timeline_entries WHERE id = ? AND user_id = ?",
                (entry_id, user_id)
            )
            
            if results:
                return self.data_manager._row_to_timeline_entry(results[0])
            return None
            
        except Exception:
            return None