"""
Flask Application Factory and Main API Routes

This module creates the Flask application and defines all API endpoints
for the SMS Hub with JWT authentication.
"""
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import logging
import os

from config import config_by_name
from models import Base, Contact, Message, PriorityLevel, RelationshipType
from jasmin_gateway import JasminSMSGateway
from ai_classifier import MessageClassifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config_name='default'):
    """
    Application factory pattern
    
    Args:
        config_name: Configuration name ('development', 'production', 'testing')
        
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    config = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(config)
    
    # Initialize extensions
    CORS(app)
    jwt = JWTManager(app)
    
    # Initialize database
    try:
        engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], pool_pre_ping=True)
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine)
        Session = scoped_session(session_factory)
        app.db_session = Session
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        app.db_session = None
    
    # Initialize Jasmin SMS Gateway
    app.sms_gateway = JasminSMSGateway(
        api_url=app.config['JASMIN_API_URL'],
        username=app.config['JASMIN_API_USERNAME'],
        password=app.config['JASMIN_API_PASSWORD']
    )
    
    # Initialize AI Message Classifier
    app.message_classifier = MessageClassifier(
        provider=app.config['AI_PROVIDER'],
        api_key=app.config.get('OPENAI_API_KEY') if app.config['AI_PROVIDER'] == 'openai' else app.config.get('GEMINI_API_KEY'),
        model=app.config.get('OPENAI_MODEL') if app.config['AI_PROVIDER'] == 'openai' else app.config.get('GEMINI_MODEL')
    )
    
    # Register routes
    register_routes(app)
    
    # Teardown database session
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if hasattr(app, 'db_session') and app.db_session:
            app.db_session.remove()
    
    return app


def register_routes(app):
    """Register all API routes"""
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'SMS Hub API'
        }), 200
    
    # Authentication endpoint
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        """
        Login endpoint to get JWT token
        
        Request body:
        {
            "username": "admin",
            "password": "password"
        }
        """
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        # Simple authentication (replace with proper user management in production)
        if username == 'admin' and password == 'admin123':
            access_token = create_access_token(identity=username)
            return jsonify({
                'access_token': access_token,
                'token_type': 'Bearer'
            }), 200
        
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Contact management endpoints
    @app.route('/api/contacts', methods=['GET'])
    @jwt_required()
    def get_contacts():
        """Get all contacts"""
        session = None
        try:
            session = app.db_session()
            contacts = session.query(Contact).all()
            return jsonify({
                'contacts': [contact.to_dict() for contact in contacts]
            }), 200
        except Exception as e:
            logger.error(f"Error fetching contacts: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            if session:
                session.close()
    
    @app.route('/api/contacts/<int:contact_id>', methods=['GET'])
    @jwt_required()
    def get_contact(contact_id):
        """Get a specific contact by ID"""
        session = None
        try:
            session = app.db_session()
            contact = session.query(Contact).filter_by(id=contact_id).first()
            if not contact:
                return jsonify({'error': 'Contact not found'}), 404
            return jsonify(contact.to_dict()), 200
        except Exception as e:
            logger.error(f"Error fetching contact: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            if session:
                session.close()
    
    @app.route('/api/contacts', methods=['POST'])
    @jwt_required()
    def create_contact():
        """
        Create a new contact
        
        Request body:
        {
            "name": "John Doe",
            "phone": "+1234567890",
            "priority": "high",
            "relationship": "parent"
        }
        """
        session = None
        try:
            data = request.get_json()
            session = app.db_session()
            
            # Validate required fields
            if not data.get('name') or not data.get('phone'):
                return jsonify({'error': 'Name and phone are required'}), 400
            
            # Check if phone already exists
            existing = session.query(Contact).filter_by(phone=data['phone']).first()
            if existing:
                return jsonify({'error': 'Contact with this phone number already exists'}), 409
            
            # Create new contact
            contact = Contact(
                name=data['name'],
                phone=data['phone'],
                priority=PriorityLevel(data.get('priority', 'medium')),
                relationship=RelationshipType(data.get('relationship', 'other'))
            )
            
            session.add(contact)
            session.commit()
            
            return jsonify(contact.to_dict()), 201
        except ValueError as e:
            if session:
                session.rollback()
            return jsonify({'error': f'Invalid value: {str(e)}'}), 400
        except Exception as e:
            logger.error(f"Error creating contact: {str(e)}")
            if session:
                session.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            if session:
                session.close()
    
    @app.route('/api/contacts/<int:contact_id>', methods=['PUT'])
    @jwt_required()
    def update_contact(contact_id):
        """Update an existing contact"""
        session = None
        try:
            data = request.get_json()
            session = app.db_session()
            
            contact = session.query(Contact).filter_by(id=contact_id).first()
            if not contact:
                return jsonify({'error': 'Contact not found'}), 404
            
            # Update fields
            if 'name' in data:
                contact.name = data['name']
            if 'phone' in data:
                # Check if new phone is already used by another contact
                existing = session.query(Contact).filter(
                    Contact.phone == data['phone'],
                    Contact.id != contact_id
                ).first()
                if existing:
                    return jsonify({'error': 'Phone number already used by another contact'}), 409
                contact.phone = data['phone']
            if 'priority' in data:
                contact.priority = PriorityLevel(data['priority'])
            if 'relationship' in data:
                contact.relationship = RelationshipType(data['relationship'])
            
            session.commit()
            return jsonify(contact.to_dict()), 200
        except ValueError as e:
            if session:
                session.rollback()
            return jsonify({'error': f'Invalid value: {str(e)}'}), 400
        except Exception as e:
            logger.error(f"Error updating contact: {str(e)}")
            if session:
                session.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            if session:
                session.close()
    
    @app.route('/api/contacts/<int:contact_id>', methods=['DELETE'])
    @jwt_required()
    def delete_contact(contact_id):
        """Delete a contact"""
        session = None
        try:
            session = app.db_session()
            contact = session.query(Contact).filter_by(id=contact_id).first()
            if not contact:
                return jsonify({'error': 'Contact not found'}), 404
            
            session.delete(contact)
            session.commit()
            return jsonify({'message': 'Contact deleted successfully'}), 200
        except Exception as e:
            logger.error(f"Error deleting contact: {str(e)}")
            if session:
                session.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            if session:
                session.close()
    
    # SMS endpoints
    @app.route('/api/sms/send', methods=['POST'])
    @jwt_required()
    def send_sms():
        """
        Send an SMS message
        
        Request body:
        {
            "to": "+1234567890",
            "content": "Hello, this is a test message",
            "from": "+0987654321" (optional)
        }
        """
        session = None
        try:
            data = request.get_json()
            
            if not data.get('to') or not data.get('content'):
                return jsonify({'error': 'to and content are required'}), 400
            
            to = data['to']
            content = data['content']
            from_number = data.get('from')
            
            # Classify message
            classification = app.message_classifier.classify_message(content)
            
            # Send SMS via Jasmin Gateway
            result = app.sms_gateway.send_sms(to, content, from_number)
            
            # Store message in database
            session = app.db_session()
            
            # Try to find contact by phone
            contact = session.query(Contact).filter_by(phone=to).first()
            
            message = Message(
                contact_id=contact.id if contact else None,
                phone=to,
                content=content,
                direction='outbound',
                status=result.get('status', 'pending'),
                classification=classification
            )
            
            session.add(message)
            session.commit()
            
            return jsonify({
                'message': 'SMS sent successfully',
                'result': result,
                'classification': classification,
                'message_id': message.id
            }), 200
            
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            if session:
                session.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            if session:
                session.close()
    
    @app.route('/api/messages', methods=['GET'])
    @jwt_required()
    def get_messages():
        """
        Get all messages with optional filters
        
        Query parameters:
        - contact_id: Filter by contact ID
        - direction: Filter by direction (inbound/outbound)
        - classification: Filter by classification (critical/stable)
        - limit: Number of messages to return (default: 100)
        """
        session = None
        try:
            session = app.db_session()
            query = session.query(Message)
            
            # Apply filters
            contact_id = request.args.get('contact_id')
            if contact_id:
                query = query.filter_by(contact_id=int(contact_id))
            
            direction = request.args.get('direction')
            if direction:
                query = query.filter_by(direction=direction)
            
            classification = request.args.get('classification')
            if classification:
                query = query.filter_by(classification=classification)
            
            # Limit and order
            limit = int(request.args.get('limit', 100))
            messages = query.order_by(Message.created_at.desc()).limit(limit).all()
            
            return jsonify({
                'messages': [message.to_dict() for message in messages],
                'count': len(messages)
            }), 200
            
        except Exception as e:
            logger.error(f"Error fetching messages: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            if session:
                session.close()
    
    @app.route('/api/messages/<int:message_id>', methods=['GET'])
    @jwt_required()
    def get_message(message_id):
        """Get a specific message by ID"""
        session = None
        try:
            session = app.db_session()
            message = session.query(Message).filter_by(id=message_id).first()
            if not message:
                return jsonify({'error': 'Message not found'}), 404
            return jsonify(message.to_dict()), 200
        except Exception as e:
            logger.error(f"Error fetching message: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            if session:
                session.close()
    
    # Jasmin Gateway status endpoints
    @app.route('/api/gateway/balance', methods=['GET'])
    @jwt_required()
    def check_balance():
        """Check SMS gateway balance"""
        try:
            result = app.sms_gateway.check_balance()
            return jsonify(result), 200
        except Exception as e:
            logger.error(f"Error checking balance: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/gateway/status/<message_id>', methods=['GET'])
    @jwt_required()
    def check_message_status(message_id):
        """Check status of a sent message"""
        try:
            result = app.sms_gateway.get_message_status(message_id)
            return jsonify(result), 200
        except Exception as e:
            logger.error(f"Error checking message status: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    # Statistics endpoint
    @app.route('/api/stats', methods=['GET'])
    @jwt_required()
    def get_stats():
        """Get system statistics"""
        session = None
        try:
            session = app.db_session()
            
            total_contacts = session.query(Contact).count()
            total_messages = session.query(Message).count()
            critical_messages = session.query(Message).filter_by(classification='critical').count()
            
            return jsonify({
                'total_contacts': total_contacts,
                'total_messages': total_messages,
                'critical_messages': critical_messages,
                'stable_messages': total_messages - critical_messages
            }), 200
            
        except Exception as e:
            logger.error(f"Error fetching stats: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            if session:
                session.close()


if __name__ == '__main__':
    # Get configuration from environment
    config_name = os.getenv('FLASK_ENV', 'development')
    app = create_app(config_name)
    
    # Run the application
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
