"""
AI Message Stabilization Module

Uses OpenAI or Google Gemini to classify messages as
'critical' or 'stable' based on content analysis.
"""
import logging
from typing import Literal, Optional, Dict

logger = logging.getLogger(__name__)


class MessageClassifier:
    """AI-powered message classification for urgency detection"""
    
    def __init__(self, provider: str = 'openai', api_key: str = '', model: str = None):
        """
        Initialize message classifier
        
        Args:
            provider: 'openai' or 'gemini'
            api_key: API key for the chosen provider
            model: Model name to use
        """
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = model
        self.client = None
        
        if self.provider == 'openai' and api_key:
            try:
                import openai
                openai.api_key = api_key
                self.client = openai
                self.model = model or 'gpt-4'
            except ImportError:
                logger.error("OpenAI package not installed")
        elif self.provider == 'gemini' and api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.client = genai
                self.model = model or 'gemini-pro'
            except ImportError:
                logger.error("Google Generative AI package not installed")
    
    def classify_message(self, content: str) -> Literal['critical', 'stable']:
        """
        Classify message as 'critical' or 'stable'
        
        Args:
            content: Message content to classify
            
        Returns:
            'critical' or 'stable'
        """
        if not self.client or not self.api_key:
            logger.warning("AI provider not configured, defaulting to stable")
            return 'stable'
        
        try:
            if self.provider == 'openai':
                return self._classify_with_openai(content)
            elif self.provider == 'gemini':
                return self._classify_with_gemini(content)
            else:
                logger.warning(f"Unknown provider: {self.provider}, defaulting to stable")
                return 'stable'
        except Exception as e:
            logger.error(f"Error classifying message: {str(e)}")
            return 'stable'
    
    def _classify_with_openai(self, content: str) -> Literal['critical', 'stable']:
        """Classify using OpenAI GPT"""
        try:
            prompt = self._get_classification_prompt(content)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a message urgency classifier. Respond with only 'critical' or 'stable'."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0
            )
            
            result = response.choices[0].message.content.strip().lower()
            
            if 'critical' in result:
                return 'critical'
            else:
                return 'stable'
                
        except Exception as e:
            logger.error(f"OpenAI classification error: {str(e)}")
            return 'stable'
    
    def _classify_with_gemini(self, content: str) -> Literal['critical', 'stable']:
        """Classify using Google Gemini"""
        try:
            prompt = self._get_classification_prompt(content)
            
            model = self.client.GenerativeModel(self.model)
            response = model.generate_content(prompt)
            
            result = response.text.strip().lower()
            
            if 'critical' in result:
                return 'critical'
            else:
                return 'stable'
                
        except Exception as e:
            logger.error(f"Gemini classification error: {str(e)}")
            return 'stable'
    
    def _get_classification_prompt(self, content: str) -> str:
        """Generate classification prompt"""
        return f"""Classify the following SMS message as either 'critical' or 'stable'.

A message is 'critical' if it contains:
- Emergency situations (fire, medical emergency, accident)
- Urgent requests for help
- Safety concerns
- Time-sensitive family matters
- Words like: emergency, urgent, help, danger, hospital, accident, fire, police

A message is 'stable' if it contains:
- General conversation
- Routine updates
- Social chat
- Non-urgent information

Message: "{content}"

Classification (respond with only 'critical' or 'stable'):"""


def analyze_message_sentiment(content: str, provider: str = 'openai', 
                              api_key: str = '', model: str = None) -> Optional[Dict]:
    """
    Analyze message sentiment and extract key information
    
    Args:
        content: Message content
        provider: 'openai' or 'gemini'
        api_key: API key
        model: Model name
        
    Returns:
        Dictionary with sentiment analysis results
    """
    if not api_key:
        return None
    
    try:
        if provider == 'openai':
            import openai
            openai.api_key = api_key
            model = model or 'gpt-4'
            
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a message sentiment analyzer. Provide a brief sentiment analysis."},
                    {"role": "user", "content": f"Analyze the sentiment of this message: {content}"}
                ],
                max_tokens=100
            )
            
            return {
                'sentiment': response.choices[0].message.content.strip(),
                'provider': 'openai'
            }
        elif provider == 'gemini':
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model_obj = genai.GenerativeModel(model or 'gemini-pro')
            
            response = model_obj.generate_content(
                f"Analyze the sentiment of this message briefly: {content}"
            )
            
            return {
                'sentiment': response.text.strip(),
                'provider': 'gemini'
            }
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        return None
