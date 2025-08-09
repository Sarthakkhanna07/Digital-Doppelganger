"""
Tone Evolution and Management System for Time Capsule AI
Learns user communication preferences and adapts responses accordingly
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import re

from models import ToneProfile, ToneAdjustment, EmotionProfile
from utils.database import DatabaseManager

class ToneManager:
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.db = data_manager.db
        
        # Base tone templates for different emotional contexts
        self.tone_templates = {
            'stress': {
                'empathetic': "I can sense you're feeling {emotion}. {message} Take your time with this.",
                'supportive': "You've got this! {message} Remember, you've handled tough situations before.",
                'gentle': "I understand this feels overwhelming. {message} One step at a time."
            },
            'excitement': {
                'enthusiastic': "I love your energy! {message} This is going to be amazing!",
                'playful': "Look at you being all excited! {message} Can't wait to see how this goes!",
                'encouraging': "Your excitement is contagious! {message} Go make it happen!"
            },
            'accomplishment': {
                'celebratory': "Way to go! {message} You should be proud of yourself!",
                'proud': "I'm so proud of you! {message} You've earned this moment.",
                'encouraging': "Look what you achieved! {message} Keep up the amazing work!"
            },
            'sadness': {
                'comforting': "I'm here with you. {message} It's okay to feel this way.",
                'gentle': "Sending you gentle thoughts. {message} Take care of yourself.",
                'supportive': "You're not alone in this. {message} Better days are coming."
            },
            'neutral': {
                'friendly': "Got it! {message} I'll make sure to remind you.",
                'casual': "Sure thing! {message} I've got you covered.",
                'professional': "Understood. {message} I will ensure you receive this reminder."
            }
        }
        
        # Time-based tone adjustments
        self.time_based_tones = {
            'morning': {'energy_boost': 0.2, 'formality_reduction': 0.1},
            'afternoon': {'focus_boost': 0.1, 'efficiency_emphasis': 0.2},
            'evening': {'gentleness_boost': 0.2, 'relaxation_emphasis': 0.1},
            'late_night': {'gentleness_boost': 0.3, 'energy_reduction': 0.2}
        }
        
        # Context-based tone adjustments
        self.context_based_tones = {
            'work': {'professionalism_boost': 0.2, 'efficiency_emphasis': 0.1},
            'exercise': {'enthusiasm_boost': 0.3, 'energy_boost': 0.2},
            'home': {'casualness_boost': 0.2, 'warmth_boost': 0.1},
            'social': {'playfulness_boost': 0.2, 'enthusiasm_boost': 0.1}
        }
    
    async def build_user_profile(self, user_id: str) -> ToneProfile:
        """Build or retrieve user's tone profile"""
        try:
            # Try to get existing profile
            results = await self.db.execute_query(
                "SELECT tone_profile FROM users WHERE id = ?",
                (user_id,)
            )
            
            if results and results[0]['tone_profile']:
                profile_data = self.db.deserialize_json(results[0]['tone_profile'])
                return self._deserialize_tone_profile(profile_data, user_id)
            
            # Create default profile for new user
            default_profile = ToneProfile(
                user_id=user_id,
                preferred_formality=0.0,  # Neutral
                preferred_energy=0.1,     # Slightly energetic
                preferred_support=0.2,    # Somewhat supportive
                preferred_playfulness=0.0, # Neutral
                time_based_preferences={},
                context_based_preferences={},
                learning_confidence=0.1,  # Low confidence initially
                last_updated=datetime.now()
            )
            
            # Store the default profile
            await self._store_tone_profile(default_profile)
            return default_profile
            
        except Exception as e:
            # Return safe default if anything fails
            return ToneProfile(
                user_id=user_id,
                preferred_formality=0.0,
                preferred_energy=0.1,
                preferred_support=0.2,
                preferred_playfulness=0.0,
                time_based_preferences={},
                context_based_preferences={},
                learning_confidence=0.1,
                last_updated=datetime.now()
            )
    
    async def adapt_response_tone(self, base_message: str, profile: ToneProfile, 
                                context: Dict[str, Any] = None) -> str:
        """Adapt response tone based on user profile and context"""
        try:
            if context is None:
                context = {}
            
            # Determine emotional context from message or context
            emotional_context = context.get('emotional_context', 'neutral')
            time_context = context.get('time_context', 'general')
            activity_context = context.get('activity_context', 'general')
            
            # Select appropriate tone template
            tone_category = self._map_emotion_to_tone_category(emotional_context)
            tone_style = self._select_tone_style(tone_category, profile)
            
            # Apply tone template if available
            if tone_category in self.tone_templates and tone_style in self.tone_templates[tone_category]:
                template = self.tone_templates[tone_category][tone_style]
                adapted_message = template.format(
                    message=base_message,
                    emotion=emotional_context
                )
            else:
                adapted_message = base_message
            
            # Apply fine-tuning based on profile preferences
            adapted_message = self._fine_tune_message(adapted_message, profile, context)
            
            return adapted_message
            
        except Exception as e:
            # Return original message if adaptation fails
            return base_message
    
    async def learn_from_interaction(self, user_id: str, interaction_data: Dict[str, Any]) -> None:
        """Learn from user interaction to improve tone profile"""
        try:
            profile = await self.build_user_profile(user_id)
            
            # Extract learning signals from interaction
            response_time = interaction_data.get('response_time_seconds', 0)
            user_feedback = interaction_data.get('user_feedback', '')
            tone_used = interaction_data.get('tone_used', {})
            context = interaction_data.get('context', {})
            
            # Quick response suggests good tone match
            if response_time < 30:  # Quick response
                self._reinforce_tone_preferences(profile, tone_used, context)
            
            # Analyze feedback for tone preferences
            if user_feedback:
                self._analyze_feedback_for_tone(profile, user_feedback, tone_used)
            
            # Update learning confidence
            profile.learning_confidence = min(1.0, profile.learning_confidence + 0.05)
            profile.last_updated = datetime.now()
            
            # Store updated profile
            await self._store_tone_profile(profile)
            
        except Exception as e:
            # Fail silently to not disrupt user experience
            pass
    
    async def predict_optimal_tone(self, context: Dict[str, Any]) -> str:
        """Predict optimal tone style for given context"""
        emotional_context = context.get('emotional_context', 'neutral')
        time_of_day = context.get('time_of_day', 'general')
        activity = context.get('activity', 'general')
        
        # Map context to tone recommendations
        tone_scores = {
            'empathetic': 0.5,
            'enthusiastic': 0.3,
            'gentle': 0.4,
            'playful': 0.2,
            'professional': 0.3,
            'casual': 0.4
        }
        
        # Adjust based on emotional context
        if emotional_context in ['stress', 'sadness', 'anxiety']:
            tone_scores['empathetic'] += 0.3
            tone_scores['gentle'] += 0.2
            tone_scores['playful'] -= 0.2
        elif emotional_context in ['excitement', 'joy', 'accomplishment']:
            tone_scores['enthusiastic'] += 0.3
            tone_scores['playful'] += 0.2
            tone_scores['gentle'] -= 0.1
        
        # Adjust based on time
        if time_of_day in ['morning']:
            tone_scores['enthusiastic'] += 0.1
        elif time_of_day in ['evening', 'late_night']:
            tone_scores['gentle'] += 0.2
            tone_scores['enthusiastic'] -= 0.1
        
        # Adjust based on activity
        if activity == 'work':
            tone_scores['professional'] += 0.2
            tone_scores['playful'] -= 0.1
        elif activity == 'exercise':
            tone_scores['enthusiastic'] += 0.2
        
        # Return highest scoring tone
        return max(tone_scores, key=tone_scores.get)
    
    def _map_emotion_to_tone_category(self, emotion: str) -> str:
        """Map emotion to tone category"""
        emotion_mapping = {
            'stress': 'stress',
            'anxiety': 'stress',
            'overwhelmed': 'stress',
            'excitement': 'excitement',
            'joy': 'excitement',
            'happy': 'excitement',
            'accomplishment': 'accomplishment',
            'proud': 'accomplishment',
            'satisfied': 'accomplishment',
            'sadness': 'sadness',
            'disappointed': 'sadness',
            'down': 'sadness'
        }
        
        return emotion_mapping.get(emotion.lower(), 'neutral')
    
    def _select_tone_style(self, tone_category: str, profile: ToneProfile) -> str:
        """Select specific tone style based on user profile"""
        if tone_category == 'stress':
            if profile.preferred_support > 0.5:
                return 'empathetic'
            elif profile.preferred_energy > 0.3:
                return 'supportive'
            else:
                return 'gentle'
        elif tone_category == 'excitement':
            if profile.preferred_energy > 0.5:
                return 'enthusiastic'
            elif profile.preferred_playfulness > 0.3:
                return 'playful'
            else:
                return 'encouraging'
        elif tone_category == 'accomplishment':
            if profile.preferred_playfulness > 0.4:
                return 'celebratory'
            elif profile.preferred_support > 0.4:
                return 'proud'
            else:
                return 'encouraging'
        elif tone_category == 'sadness':
            if profile.preferred_support > 0.6:
                return 'comforting'
            elif profile.preferred_energy < 0.3:
                return 'gentle'
            else:
                return 'supportive'
        else:  # neutral
            if profile.preferred_formality > 0.3:
                return 'professional'
            elif profile.preferred_playfulness > 0.3:
                return 'casual'
            else:
                return 'friendly'
    
    def _fine_tune_message(self, message: str, profile: ToneProfile, context: Dict[str, Any]) -> str:
        """Apply fine-tuning adjustments to message"""
        # Add enthusiasm markers if user prefers high energy
        if profile.preferred_energy > 0.6:
            if not any(punct in message for punct in ['!', '?']):
                message = message.rstrip('.') + '!'
        
        # Add supportive language if user prefers high support
        if profile.preferred_support > 0.6:
            supportive_additions = [
                "You've got this! ",
                "I believe in you! ",
                "You're doing great! "
            ]
            # Randomly add supportive language (simplified for now)
            if 'stress' in context.get('emotional_context', ''):
                message = supportive_additions[0] + message
        
        # Adjust formality
        if profile.preferred_formality < -0.3:
            # Make more casual
            message = message.replace("I will", "I'll")
            message = message.replace("you are", "you're")
            message = message.replace("cannot", "can't")
        elif profile.preferred_formality > 0.3:
            # Make more formal
            message = message.replace("I'll", "I will")
            message = message.replace("you're", "you are")
            message = message.replace("can't", "cannot")
        
        return message
    
    def _reinforce_tone_preferences(self, profile: ToneProfile, tone_used: Dict[str, Any], 
                                  context: Dict[str, Any]) -> None:
        """Reinforce tone preferences based on positive interaction"""
        # This is a simplified reinforcement learning approach
        learning_rate = 0.1 * profile.learning_confidence
        
        # Reinforce the tone dimensions that were used successfully
        if tone_used.get('energy_level', 0) > 0.5:
            profile.preferred_energy = min(1.0, profile.preferred_energy + learning_rate)
        
        if tone_used.get('support_level', 0) > 0.5:
            profile.preferred_support = min(1.0, profile.preferred_support + learning_rate)
        
        if tone_used.get('playfulness_level', 0) > 0.5:
            profile.preferred_playfulness = min(1.0, profile.preferred_playfulness + learning_rate)
        
        if tone_used.get('formality_level', 0) > 0.5:
            profile.preferred_formality = min(1.0, profile.preferred_formality + learning_rate)
    
    def _analyze_feedback_for_tone(self, profile: ToneProfile, feedback: str, tone_used: Dict[str, Any]) -> None:
        """Analyze user feedback to adjust tone preferences"""
        feedback_lower = feedback.lower()
        
        # Positive feedback indicators
        positive_indicators = ['love', 'great', 'perfect', 'awesome', 'thanks', 'helpful']
        negative_indicators = ['too much', 'annoying', 'weird', 'formal', 'casual']
        
        is_positive = any(indicator in feedback_lower for indicator in positive_indicators)
        is_negative = any(indicator in feedback_lower for indicator in negative_indicators)
        
        learning_rate = 0.15
        
        if is_positive:
            # Reinforce current tone settings
            self._reinforce_tone_preferences(profile, tone_used, {})
        elif is_negative:
            # Adjust away from current tone settings
            if tone_used.get('energy_level', 0) > 0.5:
                profile.preferred_energy = max(-1.0, profile.preferred_energy - learning_rate)
            if tone_used.get('playfulness_level', 0) > 0.5:
                profile.preferred_playfulness = max(-1.0, profile.preferred_playfulness - learning_rate)
    
    async def _store_tone_profile(self, profile: ToneProfile) -> None:
        """Store tone profile in database"""
        try:
            profile_data = {
                'preferred_formality': profile.preferred_formality,
                'preferred_energy': profile.preferred_energy,
                'preferred_support': profile.preferred_support,
                'preferred_playfulness': profile.preferred_playfulness,
                'time_based_preferences': profile.time_based_preferences,
                'context_based_preferences': profile.context_based_preferences,
                'learning_confidence': profile.learning_confidence,
                'last_updated': profile.last_updated.isoformat()
            }
            
            await self.db.execute_update(
                "UPDATE users SET tone_profile = ? WHERE id = ?",
                (self.db.serialize_json(profile_data), profile.user_id)
            )
            
        except Exception as e:
            # Fail silently to not disrupt user experience
            pass
    
    def _deserialize_tone_profile(self, data: Dict[str, Any], user_id: str) -> ToneProfile:
        """Deserialize tone profile from database data"""
        return ToneProfile(
            user_id=user_id,
            preferred_formality=data.get('preferred_formality', 0.0),
            preferred_energy=data.get('preferred_energy', 0.1),
            preferred_support=data.get('preferred_support', 0.2),
            preferred_playfulness=data.get('preferred_playfulness', 0.0),
            time_based_preferences=data.get('time_based_preferences', {}),
            context_based_preferences=data.get('context_based_preferences', {}),
            learning_confidence=data.get('learning_confidence', 0.1),
            last_updated=datetime.fromisoformat(data.get('last_updated', datetime.now().isoformat()))
        )