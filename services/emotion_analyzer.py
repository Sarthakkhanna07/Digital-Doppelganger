"""
Emotion Detection and Analysis Engine for Time Capsule AI
Analyzes emotional state from text and context
"""

import re
from typing import Dict, List, Any
from datetime import datetime

from models import EmotionProfile

class EmotionAnalyzer:
    def __init__(self):
        # Emotion lexicons with intensity weights
        self.emotion_lexicon = {
            'joy': {
                'high': ['ecstatic', 'thrilled', 'overjoyed', 'elated', 'euphoric'],
                'medium': ['happy', 'pleased', 'glad', 'cheerful', 'content'],
                'low': ['okay', 'fine', 'alright', 'decent']
            },
            'sadness': {
                'high': ['devastated', 'heartbroken', 'miserable', 'depressed'],
                'medium': ['sad', 'down', 'upset', 'disappointed', 'blue'],
                'low': ['meh', 'blah', 'not great']
            },
            'anger': {
                'high': ['furious', 'enraged', 'livid', 'irate'],
                'medium': ['angry', 'mad', 'annoyed', 'frustrated', 'irritated'],
                'low': ['bothered', 'mildly annoyed']
            },
            'fear': {
                'high': ['terrified', 'petrified', 'horrified'],
                'medium': ['scared', 'afraid', 'worried', 'nervous', 'anxious'],
                'low': ['concerned', 'uneasy', 'apprehensive']
            },
            'surprise': {
                'high': ['shocked', 'stunned', 'amazed', 'astonished'],
                'medium': ['surprised', 'unexpected', 'wow'],
                'low': ['interesting', 'huh', 'oh']
            },
            'disgust': {
                'high': ['revolted', 'sickened', 'appalled'],
                'medium': ['disgusted', 'gross', 'yuck'],
                'low': ['not impressed', 'meh']
            },
            'excitement': {
                'high': ['pumped', 'stoked', 'psyched', 'can\'t wait'],
                'medium': ['excited', 'looking forward', 'eager'],
                'low': ['interested', 'curious']
            },
            'stress': {
                'high': ['overwhelmed', 'swamped', 'drowning', 'breaking down'],
                'medium': ['stressed', 'pressured', 'tense', 'frazzled'],
                'low': ['busy', 'tight schedule', 'a bit much']
            },
            'accomplishment': {
                'high': ['triumphant', 'victorious', 'achieved everything'],
                'medium': ['accomplished', 'proud', 'satisfied', 'done'],
                'low': ['finished', 'completed', 'got it done']
            },
            'anxiety': {
                'high': ['panicking', 'freaking out', 'having a breakdown'],
                'medium': ['anxious', 'worried sick', 'on edge'],
                'low': ['a bit worried', 'slightly concerned']
            },
            'contentment': {
                'high': ['blissful', 'at peace', 'completely satisfied'],
                'medium': ['content', 'satisfied', 'comfortable'],
                'low': ['okay with this', 'fine', 'decent']
            }
        }
        
        # Contextual emotion modifiers
        self.context_modifiers = {
            'work': {
                'stress_multiplier': 1.3,
                'accomplishment_multiplier': 1.2,
                'common_emotions': ['stress', 'accomplishment', 'frustration']
            },
            'exercise': {
                'accomplishment_multiplier': 1.4,
                'excitement_multiplier': 1.2,
                'common_emotions': ['accomplishment', 'excitement', 'satisfaction']
            },
            'home': {
                'contentment_multiplier': 1.2,
                'relaxation_multiplier': 1.3,
                'common_emotions': ['contentment', 'relaxation', 'comfort']
            },
            'social': {
                'joy_multiplier': 1.2,
                'excitement_multiplier': 1.1,
                'common_emotions': ['joy', 'excitement', 'connection']
            }
        }
        
        # Time-based emotion patterns
        self.time_patterns = {
            'morning': ['energetic', 'fresh', 'ready', 'motivated'],
            'afternoon': ['focused', 'productive', 'busy'],
            'evening': ['tired', 'winding down', 'reflective', 'relaxed'],
            'late_night': ['tired', 'contemplative', 'quiet']
        }
        
        # Intensity indicators
        self.intensity_amplifiers = [
            'really', 'very', 'extremely', 'super', 'incredibly', 'absolutely',
            'totally', 'completely', 'utterly', 'so', 'quite', 'pretty'
        ]
        
        self.intensity_diminishers = [
            'a bit', 'slightly', 'somewhat', 'kind of', 'sort of', 'a little',
            'not too', 'barely', 'hardly'
        ]
    
    async def analyze_emotion(self, text: str, context: Dict[str, Any]) -> EmotionProfile:
        """
        Analyze emotional state from text and context
        Returns comprehensive emotion profile
        """
        text_lower = text.lower()
        
        # Detect emotions from text
        detected_emotions = self._detect_emotions_from_text(text_lower)
        
        # Apply contextual modifiers
        if context.get('activity_context'):
            detected_emotions = self._apply_context_modifiers(
                detected_emotions, context['activity_context']
            )
        
        # Apply time-based patterns
        if context.get('time_of_day'):
            detected_emotions = self._apply_time_patterns(
                detected_emotions, context['time_of_day']
            )
        
        # Determine primary emotion
        primary_emotion = max(detected_emotions, key=detected_emotions.get) if detected_emotions else 'neutral'
        primary_intensity = detected_emotions.get(primary_emotion, 0.5)
        
        # Get secondary emotions (excluding primary)
        secondary_emotions = {k: v for k, v in detected_emotions.items() if k != primary_emotion}
        
        # Calculate confidence based on number of indicators found
        confidence = min(1.0, len(self._get_emotion_indicators(text_lower)) * 0.2 + 0.3)
        
        # Get detected indicators for transparency
        indicators = self._get_emotion_indicators(text_lower)
        
        # Build contextual factors
        contextual_factors = {
            'time_of_day': context.get('time_of_day'),
            'day_of_week': context.get('day_of_week'),
            'activity_context': context.get('activity_context'),
            'detected_amplifiers': self._detect_intensity_modifiers(text_lower),
            'text_length': len(text),
            'exclamation_count': text.count('!'),
            'question_count': text.count('?'),
            'caps_ratio': sum(1 for c in text if c.isupper()) / len(text) if text else 0
        }
        
        return EmotionProfile(
            primary_emotion=primary_emotion,
            intensity=primary_intensity,
            secondary_emotions=secondary_emotions,
            confidence_score=confidence,
            detected_indicators=indicators,
            contextual_factors=contextual_factors
        )
    
    async def detect_stress_indicators(self, text: str) -> str:
        """Detect stress level from text"""
        text_lower = text.lower()
        stress_score = 0
        
        # Check for stress-related words
        for intensity, words in self.emotion_lexicon['stress'].items():
            for word in words:
                if word in text_lower:
                    if intensity == 'high':
                        stress_score += 3
                    elif intensity == 'medium':
                        stress_score += 2
                    else:
                        stress_score += 1
        
        # Check for additional stress indicators
        stress_indicators = [
            'deadline', 'pressure', 'overwhelmed', 'too much', 'can\'t handle',
            'breaking point', 'exhausted', 'burned out', 'swamped'
        ]
        
        for indicator in stress_indicators:
            if indicator in text_lower:
                stress_score += 1
        
        # Classify stress level
        if stress_score >= 5:
            return 'high'
        elif stress_score >= 3:
            return 'medium'
        elif stress_score >= 1:
            return 'low'
        else:
            return 'none'
    
    def _detect_emotions_from_text(self, text: str) -> Dict[str, float]:
        """Detect emotions from text using lexicon matching"""
        detected_emotions = {}
        
        for emotion, intensity_levels in self.emotion_lexicon.items():
            emotion_score = 0
            
            for intensity, words in intensity_levels.items():
                for word in words:
                    if word in text:
                        # Base score based on intensity
                        base_score = {'high': 0.9, 'medium': 0.6, 'low': 0.3}[intensity]
                        
                        # Apply intensity modifiers
                        modified_score = self._apply_intensity_modifiers(text, word, base_score)
                        emotion_score = max(emotion_score, modified_score)
            
            if emotion_score > 0:
                detected_emotions[emotion] = emotion_score
        
        return detected_emotions
    
    def _apply_intensity_modifiers(self, text: str, word: str, base_score: float) -> float:
        """Apply intensity modifiers based on surrounding words"""
        word_index = text.find(word)
        if word_index == -1:
            return base_score
        
        # Check words before the emotion word
        words_before = text[:word_index].split()[-3:]  # Check last 3 words
        
        # Check for amplifiers
        for amplifier in self.intensity_amplifiers:
            if amplifier in words_before:
                return min(1.0, base_score * 1.3)
        
        # Check for diminishers
        for diminisher in self.intensity_diminishers:
            if diminisher in words_before:
                return max(0.1, base_score * 0.7)
        
        return base_score
    
    def _apply_context_modifiers(self, emotions: Dict[str, float], activity: str) -> Dict[str, float]:
        """Apply contextual modifiers based on activity"""
        if activity not in self.context_modifiers:
            return emotions
        
        modifiers = self.context_modifiers[activity]
        modified_emotions = emotions.copy()
        
        for emotion, score in emotions.items():
            modifier_key = f"{emotion}_multiplier"
            if modifier_key in modifiers:
                modified_emotions[emotion] = min(1.0, score * modifiers[modifier_key])
        
        return modified_emotions
    
    def _apply_time_patterns(self, emotions: Dict[str, float], time_context: str) -> Dict[str, float]:
        """Apply time-based emotional patterns"""
        if time_context not in self.time_patterns:
            return emotions
        
        time_emotions = self.time_patterns[time_context]
        modified_emotions = emotions.copy()
        
        # Boost emotions that are common for this time
        for emotion in emotions:
            if emotion in time_emotions:
                modified_emotions[emotion] = min(1.0, emotions[emotion] * 1.1)
        
        return modified_emotions
    
    def _get_emotion_indicators(self, text: str) -> List[str]:
        """Get list of emotion indicators found in text"""
        indicators = []
        
        for emotion, intensity_levels in self.emotion_lexicon.items():
            for intensity, words in intensity_levels.items():
                for word in words:
                    if word in text:
                        indicators.append(f"{word} ({emotion})")
        
        return indicators
    
    def _detect_intensity_modifiers(self, text: str) -> Dict[str, List[str]]:
        """Detect intensity modifiers in text"""
        found_amplifiers = [amp for amp in self.intensity_amplifiers if amp in text]
        found_diminishers = [dim for dim in self.intensity_diminishers if dim in text]
        
        return {
            'amplifiers': found_amplifiers,
            'diminishers': found_diminishers
        }