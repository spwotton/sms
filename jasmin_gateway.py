"""
Jasmin SMS Gateway Integration Module

Provides integration with Jasmin SMS Gateway for sending
and receiving SMS messages via GSM modem.
"""
import requests
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class JasminSMSGateway:
    """Jasmin SMS Gateway client for sending SMS messages"""
    
    def __init__(self, api_url: str, username: str, password: str):
        """
        Initialize Jasmin SMS Gateway client
        
        Args:
            api_url: Base URL of Jasmin API (e.g., http://localhost:8080)
            username: Jasmin API username
            password: Jasmin API password
        """
        self.api_url = api_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)
    
    def send_sms(self, to: str, content: str, from_number: Optional[str] = None) -> Dict:
        """
        Send an SMS message via Jasmin Gateway
        
        Args:
            to: Recipient phone number (international format)
            content: Message content
            from_number: Optional sender phone number
            
        Returns:
            Dictionary with status and message_id or error
        """
        try:
            # Jasmin REST API endpoint for sending SMS
            url = f"{self.api_url}/secure/send"
            
            params = {
                'username': self.username,
                'password': self.password,
                'to': to,
                'content': content
            }
            
            if from_number:
                params['from'] = from_number
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                # Jasmin returns "Success <message_id>" on success
                response_text = response.text.strip()
                if response_text.startswith('Success'):
                    message_id = response_text.split()[-1] if len(response_text.split()) > 1 else None
                    logger.info(f"SMS sent successfully to {to}, message_id: {message_id}")
                    return {
                        'status': 'sent',
                        'message_id': message_id,
                        'to': to
                    }
                else:
                    logger.error(f"Unexpected response from Jasmin: {response_text}")
                    return {
                        'status': 'failed',
                        'error': response_text
                    }
            else:
                logger.error(f"Failed to send SMS: HTTP {response.status_code}")
                return {
                    'status': 'failed',
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except requests.RequestException as e:
            logger.error(f"Error connecting to Jasmin Gateway: {str(e)}")
            return {
                'status': 'failed',
                'error': f"Connection error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def check_balance(self) -> Dict:
        """
        Check SMS balance (if supported by Jasmin configuration)
        
        Returns:
            Dictionary with balance information or error
        """
        try:
            url = f"{self.api_url}/secure/balance"
            params = {
                'username': self.username,
                'password': self.password
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return {
                    'status': 'success',
                    'balance': response.text.strip()
                }
            else:
                return {
                    'status': 'failed',
                    'error': f"HTTP {response.status_code}"
                }
        except Exception as e:
            logger.error(f"Error checking balance: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def get_message_status(self, message_id: str) -> Dict:
        """
        Get status of a sent message
        
        Args:
            message_id: ID of the message to check
            
        Returns:
            Dictionary with message status
        """
        try:
            url = f"{self.api_url}/secure/dlr"
            params = {
                'username': self.username,
                'password': self.password,
                'message_id': message_id
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return {
                    'status': 'success',
                    'message_status': response.text.strip()
                }
            else:
                return {
                    'status': 'failed',
                    'error': f"HTTP {response.status_code}"
                }
        except Exception as e:
            logger.error(f"Error checking message status: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
