"""
Example script demonstrating SMS Hub API usage

This script shows how to interact with the SMS Hub API
to manage contacts and send messages.
"""
import requests
import json

# Configuration
API_BASE_URL = "http://localhost:5000/api"
USERNAME = "admin"
PASSWORD = "admin123"


class SMSHubClient:
    """Client for interacting with SMS Hub API"""
    
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = None
    
    def login(self):
        """Authenticate and get JWT token"""
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"username": self.username, "password": self.password}
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            print("✓ Successfully logged in")
            return True
        else:
            print(f"✗ Login failed: {response.text}")
            return False
    
    def get_headers(self):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.token}"}
    
    def create_contact(self, name, phone, priority="medium", relationship="other"):
        """Create a new contact"""
        response = requests.post(
            f"{self.base_url}/contacts",
            headers=self.get_headers(),
            json={
                "name": name,
                "phone": phone,
                "priority": priority,
                "relationship": relationship
            }
        )
        if response.status_code == 201:
            contact = response.json()
            print(f"✓ Contact created: {contact['name']} ({contact['phone']})")
            return contact
        else:
            print(f"✗ Failed to create contact: {response.text}")
            return None
    
    def get_contacts(self):
        """Get all contacts"""
        response = requests.get(
            f"{self.base_url}/contacts",
            headers=self.get_headers()
        )
        if response.status_code == 200:
            contacts = response.json()["contacts"]
            print(f"✓ Retrieved {len(contacts)} contacts")
            return contacts
        else:
            print(f"✗ Failed to get contacts: {response.text}")
            return []
    
    def send_sms(self, to, content, from_number=None):
        """Send an SMS message"""
        data = {"to": to, "content": content}
        if from_number:
            data["from"] = from_number
        
        response = requests.post(
            f"{self.base_url}/sms/send",
            headers=self.get_headers(),
            json=data
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✓ SMS sent to {to}")
            print(f"  Classification: {result['classification']}")
            return result
        else:
            print(f"✗ Failed to send SMS: {response.text}")
            return None
    
    def get_messages(self, limit=10, classification=None):
        """Get messages"""
        params = {"limit": limit}
        if classification:
            params["classification"] = classification
        
        response = requests.get(
            f"{self.base_url}/messages",
            headers=self.get_headers(),
            params=params
        )
        if response.status_code == 200:
            messages = response.json()["messages"]
            print(f"✓ Retrieved {len(messages)} messages")
            return messages
        else:
            print(f"✗ Failed to get messages: {response.text}")
            return []
    
    def get_stats(self):
        """Get system statistics"""
        response = requests.get(
            f"{self.base_url}/stats",
            headers=self.get_headers()
        )
        if response.status_code == 200:
            stats = response.json()
            print("✓ System Statistics:")
            print(f"  Total Contacts: {stats['total_contacts']}")
            print(f"  Total Messages: {stats['total_messages']}")
            print(f"  Critical Messages: {stats['critical_messages']}")
            print(f"  Stable Messages: {stats['stable_messages']}")
            return stats
        else:
            print(f"✗ Failed to get stats: {response.text}")
            return None


def main():
    """Example usage"""
    print("=== SMS Hub API Example ===\n")
    
    # Create client and login
    client = SMSHubClient(API_BASE_URL, USERNAME, PASSWORD)
    
    if not client.login():
        print("Failed to authenticate")
        return
    
    print("\n--- Creating Contacts ---")
    # Create some contacts
    client.create_contact("Mom", "+1234567890", priority="critical", relationship="parent")
    client.create_contact("Dad", "+0987654321", priority="critical", relationship="parent")
    client.create_contact("Sister", "+1122334455", priority="high", relationship="sibling")
    client.create_contact("Friend", "+5544332211", priority="medium", relationship="friend")
    
    print("\n--- Listing Contacts ---")
    # Get all contacts
    contacts = client.get_contacts()
    for contact in contacts:
        print(f"  - {contact['name']}: {contact['phone']} ({contact['priority']})")
    
    print("\n--- Sending Messages ---")
    # Send some test messages
    client.send_sms("+1234567890", "Hi Mom, just checking in!")
    client.send_sms("+0987654321", "URGENT: Need help immediately!")
    client.send_sms("+1122334455", "See you at dinner tonight")
    
    print("\n--- Getting Recent Messages ---")
    # Get recent messages
    messages = client.get_messages(limit=5)
    for msg in messages:
        print(f"  [{msg['classification']}] {msg['phone']}: {msg['content'][:50]}...")
    
    print("\n--- Getting Critical Messages ---")
    # Get only critical messages
    critical = client.get_messages(classification="critical")
    for msg in critical:
        print(f"  [CRITICAL] {msg['phone']}: {msg['content']}")
    
    print("\n--- System Statistics ---")
    # Get system stats
    client.get_stats()
    
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Make sure the server is running at", API_BASE_URL)
    except Exception as e:
        print(f"Error: {str(e)}")
