"""
Test suite for SMS Hub API

Tests API endpoints, authentication, and core functionality
"""
import pytest
import json
from app import create_app
from models import Base, Contact, Message, PriorityLevel, RelationshipType


@pytest.fixture
def app():
    """Create and configure a test application instance"""
    app = create_app('testing')
    
    # Setup database
    with app.app_context():
        Base.metadata.create_all(app.db_session.bind)
    
    yield app
    
    # Teardown
    with app.app_context():
        Base.metadata.drop_all(app.db_session.bind)


@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """Get authentication headers with JWT token"""
    response = client.post('/api/auth/login', json={
        'username': 'admin',
        'password': 'admin123'
    })
    token = json.loads(response.data)['access_token']
    return {'Authorization': f'Bearer {token}'}


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'


def test_login_success(client):
    """Test successful login"""
    response = client.post('/api/auth/login', json={
        'username': 'admin',
        'password': 'admin123'
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'access_token' in data
    assert data['token_type'] == 'Bearer'


def test_login_failure(client):
    """Test failed login with wrong credentials"""
    response = client.post('/api/auth/login', json={
        'username': 'admin',
        'password': 'wrong'
    })
    assert response.status_code == 401


def test_create_contact(client, auth_headers):
    """Test creating a new contact"""
    response = client.post('/api/contacts', 
        headers=auth_headers,
        json={
            'name': 'Test User',
            'phone': '+1234567890',
            'priority': 'high',
            'relationship': 'friend'
        })
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['name'] == 'Test User'
    assert data['phone'] == '+1234567890'
    assert data['priority'] == 'high'


def test_get_contacts(client, auth_headers):
    """Test getting all contacts"""
    # Create a contact first
    client.post('/api/contacts', 
        headers=auth_headers,
        json={
            'name': 'Test User',
            'phone': '+1234567890',
            'priority': 'medium',
            'relationship': 'friend'
        })
    
    response = client.get('/api/contacts', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'contacts' in data
    assert len(data['contacts']) > 0


def test_get_single_contact(client, auth_headers):
    """Test getting a single contact by ID"""
    # Create a contact
    create_response = client.post('/api/contacts', 
        headers=auth_headers,
        json={
            'name': 'Test User',
            'phone': '+1234567890',
            'priority': 'high',
            'relationship': 'parent'
        })
    contact_id = json.loads(create_response.data)['id']
    
    # Get the contact
    response = client.get(f'/api/contacts/{contact_id}', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['id'] == contact_id
    assert data['name'] == 'Test User'


def test_update_contact(client, auth_headers):
    """Test updating a contact"""
    # Create a contact
    create_response = client.post('/api/contacts', 
        headers=auth_headers,
        json={
            'name': 'Test User',
            'phone': '+1234567890',
            'priority': 'medium',
            'relationship': 'friend'
        })
    contact_id = json.loads(create_response.data)['id']
    
    # Update the contact
    response = client.put(f'/api/contacts/{contact_id}',
        headers=auth_headers,
        json={
            'name': 'Updated User',
            'priority': 'critical'
        })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['name'] == 'Updated User'
    assert data['priority'] == 'critical'


def test_delete_contact(client, auth_headers):
    """Test deleting a contact"""
    # Create a contact
    create_response = client.post('/api/contacts', 
        headers=auth_headers,
        json={
            'name': 'Test User',
            'phone': '+1234567890',
            'priority': 'medium',
            'relationship': 'friend'
        })
    contact_id = json.loads(create_response.data)['id']
    
    # Delete the contact
    response = client.delete(f'/api/contacts/{contact_id}', headers=auth_headers)
    assert response.status_code == 200
    
    # Verify it's deleted
    response = client.get(f'/api/contacts/{contact_id}', headers=auth_headers)
    assert response.status_code == 404


def test_duplicate_phone_contact(client, auth_headers):
    """Test that duplicate phone numbers are rejected"""
    # Create first contact
    client.post('/api/contacts', 
        headers=auth_headers,
        json={
            'name': 'User One',
            'phone': '+1234567890',
            'priority': 'medium',
            'relationship': 'friend'
        })
    
    # Try to create duplicate
    response = client.post('/api/contacts', 
        headers=auth_headers,
        json={
            'name': 'User Two',
            'phone': '+1234567890',
            'priority': 'high',
            'relationship': 'parent'
        })
    assert response.status_code == 409


def test_get_messages(client, auth_headers):
    """Test getting messages"""
    response = client.get('/api/messages', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'messages' in data
    assert 'count' in data


def test_get_stats(client, auth_headers):
    """Test getting system statistics"""
    response = client.get('/api/stats', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'total_contacts' in data
    assert 'total_messages' in data
    assert 'critical_messages' in data


def test_unauthorized_access(client):
    """Test that endpoints require authentication"""
    response = client.get('/api/contacts')
    assert response.status_code == 401


def test_invalid_priority_value(client, auth_headers):
    """Test that invalid priority values are rejected"""
    response = client.post('/api/contacts', 
        headers=auth_headers,
        json={
            'name': 'Test User',
            'phone': '+1234567890',
            'priority': 'invalid_priority',
            'relationship': 'friend'
        })
    assert response.status_code == 400


def test_missing_required_fields(client, auth_headers):
    """Test that missing required fields are rejected"""
    response = client.post('/api/contacts', 
        headers=auth_headers,
        json={
            'name': 'Test User'
            # Missing phone
        })
    assert response.status_code == 400
