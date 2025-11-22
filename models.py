"""
Database Models Module

Defines SQLAlchemy models for the SMS Hub application:
- Contact: Store contact information with priority and relationship
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import enum

Base = declarative_base()


class PriorityLevel(enum.Enum):
    """Contact priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RelationshipType(enum.Enum):
    """Relationship types"""
    PARENT = "parent"
    CHILD = "child"
    SIBLING = "sibling"
    SPOUSE = "spouse"
    FRIEND = "friend"
    EXTENDED_FAMILY = "extended_family"
    OTHER = "other"


class Contact(Base):
    """
    Contact model for storing family/friend contact information
    
    MySQL Schema:
    CREATE TABLE contacts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        phone VARCHAR(20) NOT NULL UNIQUE,
        priority ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
        relationship ENUM('parent', 'child', 'sibling', 'spouse', 'friend', 'extended_family', 'other') DEFAULT 'other',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_priority (priority),
        INDEX idx_phone (phone)
    );
    """
    __tablename__ = 'contacts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, unique=True, index=True)
    priority = Column(Enum(PriorityLevel), default=PriorityLevel.MEDIUM, index=True)
    relationship = Column(Enum(RelationshipType), default=RelationshipType.OTHER)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'priority': self.priority.value if self.priority else None,
            'relationship': self.relationship.value if self.relationship else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Message(Base):
    """
    Message model for storing SMS messages
    
    MySQL Schema:
    CREATE TABLE messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        contact_id INT,
        phone VARCHAR(20) NOT NULL,
        content TEXT NOT NULL,
        direction ENUM('inbound', 'outbound') NOT NULL,
        status ENUM('pending', 'sent', 'delivered', 'failed') DEFAULT 'pending',
        classification ENUM('stable', 'critical') DEFAULT 'stable',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
        INDEX idx_contact (contact_id),
        INDEX idx_status (status),
        INDEX idx_created (created_at)
    );
    """
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, nullable=True)
    phone = Column(String(20), nullable=False)
    content = Column(String(1000), nullable=False)
    direction = Column(Enum('inbound', 'outbound', name='direction_enum'), nullable=False)
    status = Column(Enum('pending', 'sent', 'delivered', 'failed', name='status_enum'), default='pending')
    classification = Column(Enum('stable', 'critical', name='classification_enum'), default='stable')
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'contact_id': self.contact_id,
            'phone': self.phone,
            'content': self.content,
            'direction': self.direction,
            'status': self.status,
            'classification': self.classification,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# Database initialization function
def init_db(database_uri):
    """Initialize database connection and create tables"""
    engine = create_engine(database_uri, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Create a new database session"""
    Session = sessionmaker(bind=engine)
    return Session()
