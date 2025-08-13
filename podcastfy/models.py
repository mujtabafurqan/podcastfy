"""
Database models for Podcastfy async API.

This module defines SQLAlchemy models for tracking podcast generation jobs
in the async job processing system.
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, create_engine
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

Base = declarative_base()

class Podcast(Base):
    """
    SQLAlchemy model for podcast generation jobs.
    
    Tracks the state and metadata of podcast generation requests,
    including status, timing information, and file references.
    """
    __tablename__ = "podcasts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String, unique=True, nullable=False)
    title = Column(String)
    audio_filename = Column(String)
    audio_url = Column(String)  # Direct URL to R2 storage
    status = Column(String, nullable=False, default='queued')
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration = Column(Integer)  # in seconds
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    def to_dict(self):
        """
        Convert model instance to dictionary for API responses.
        
        Returns:
            dict: Dictionary representation suitable for JSON serialization
        """
        return {
            'id': str(self.id),
            'url': self.url,
            'title': self.title,
            'audio_url': self.audio_url if self.audio_url else (f'/api/audio/{self.id}' if self.status == 'completed' else None),
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration': self.duration,
            'error_message': self.error_message,
            'retry_count': self.retry_count
        }