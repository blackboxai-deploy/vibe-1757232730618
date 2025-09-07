"""
Database models for French Real Estate Rental Hunter
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.sqlite import JSON

from config.settings import Config

# Database setup
Base = declarative_base()
engine = None
SessionLocal = None

class PropertyStatus(Enum):
    """Status of a rental property"""
    NEW = "new"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    VISIT_SCHEDULED = "visit_scheduled"
    VISITED = "visited"
    APPLICATION_SENT = "application_sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNAVAILABLE = "unavailable"
    DUPLICATE = "duplicate"

class ContactStatus(Enum):
    """Status of contact attempts"""
    PENDING = "pending"
    EMAIL_SENT = "email_sent"
    PHONE_CALLED = "phone_called"
    RESPONDED = "responded"
    NO_RESPONSE = "no_response"
    FAILED = "failed"
    BLOCKED = "blocked"

class ContactMethod(Enum):
    """Method of contact"""
    EMAIL = "email"
    PHONE = "phone"
    BOTH = "both"

class Property(Base):
    """Rental property model"""
    __tablename__ = "properties"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    rooms = Column(Integer)
    area = Column(Float)  # in square meters
    property_type = Column(String(50))  # apartment, house, studio
    address = Column(String(500))
    city = Column(String(100), nullable=False)
    postal_code = Column(String(10))
    neighborhood = Column(String(100))
    latitude = Column(Float)
    longitude = Column(Float)
    source_site = Column(String(50), nullable=False)  # seloger, leboncoin, etc.
    source_url = Column(String(1000), nullable=False, unique=True)
    source_id = Column(String(100))
    features = Column(JSON)  # balcony, parking, elevator, etc.
    images = Column(JSON)  # list of image URLs
    status = Column(SQLEnum(PropertyStatus), default=PropertyStatus.NEW)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    still_available = Column(Boolean, default=True)
    duplicate_of = Column(Integer, ForeignKey('properties.id'), nullable=True)
    similarity_score = Column(Float)  # similarity to the original property
    
    # Relationships
    contacts = relationship("Contact", back_populates="property", cascade="all, delete-orphan")
    communications = relationship("Communication", back_populates="property", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert property to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'price': self.price,
            'rooms': self.rooms,
            'area': self.area,
            'property_type': self.property_type,
            'address': self.address,
            'city': self.city,
            'postal_code': self.postal_code,
            'neighborhood': self.neighborhood,
            'source_site': self.source_site,
            'source_url': self.source_url,
            'features': self.features or {},
            'images': self.images or [],
            'status': self.status.value if self.status else None,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'still_available': self.still_available
        }

class Contact(Base):
    """Contact information for property agencies/owners"""
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    agency_name = Column(String(200))
    email = Column(String(200))
    phone = Column(String(20))
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=False)
    status = Column(SQLEnum(ContactStatus), default=ContactStatus.PENDING)
    preferred_method = Column(SQLEnum(ContactMethod), default=ContactMethod.EMAIL)
    contact_attempts = Column(Integer, default=0)
    last_contact_attempt = Column(DateTime)
    next_contact_scheduled = Column(DateTime)
    responded = Column(Boolean, default=False)
    response_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    property = relationship("Property", back_populates="contacts")
    communications = relationship("Communication", back_populates="contact", cascade="all, delete-orphan")
    
    def schedule_follow_up(self, delay_hours: int = 24):
        """Schedule next contact attempt"""
        self.next_contact_scheduled = datetime.utcnow() + timedelta(hours=delay_hours)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert contact to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'agency_name': self.agency_name,
            'email': self.email,
            'phone': self.phone,
            'property_id': self.property_id,
            'status': self.status.value if self.status else None,
            'preferred_method': self.preferred_method.value if self.preferred_method else None,
            'contact_attempts': self.contact_attempts,
            'last_contact_attempt': self.last_contact_attempt.isoformat() if self.last_contact_attempt else None,
            'next_contact_scheduled': self.next_contact_scheduled.isoformat() if self.next_contact_scheduled else None,
            'responded': self.responded,
            'response_date': self.response_date.isoformat() if self.response_date else None
        }

class Communication(Base):
    """Individual communication records"""
    __tablename__ = "communications"
    
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=False)
    contact_id = Column(Integer, ForeignKey('contacts.id'), nullable=False)
    method = Column(SQLEnum(ContactMethod), nullable=False)
    subject = Column(String(500))
    message = Column(Text)
    status = Column(String(50))  # sent, delivered, failed, responded
    sent_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime)
    response_received_at = Column(DateTime)
    response_subject = Column(String(500))
    response_message = Column(Text)
    metadata = Column(JSON)  # additional data like email headers, call duration, etc.
    
    # Relationships
    property = relationship("Property", back_populates="communications")
    contact = relationship("Contact", back_populates="communications")

class ScrapingLog(Base):
    """Log of scraping activities"""
    __tablename__ = "scraping_logs"
    
    id = Column(Integer, primary_key=True)
    site = Column(String(50), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    properties_found = Column(Integer, default=0)
    properties_new = Column(Integer, default=0)
    properties_updated = Column(Integer, default=0)
    properties_duplicates = Column(Integer, default=0)
    status = Column(String(50))  # running, completed, failed
    error_message = Column(Text)
    search_criteria = Column(JSON)
    metadata = Column(JSON)

def init_db():
    """Initialize database connection and create tables"""
    global engine, SessionLocal
    
    config = Config()
    engine = create_engine(
        config.DATABASE_URL,
        echo=config.DEBUG,
        pool_pre_ping=True
    )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise

def close_db():
    """Close database connection"""
    if engine:
        engine.dispose()