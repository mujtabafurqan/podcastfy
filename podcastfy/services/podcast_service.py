"""
Service layer for podcast operations.

This module provides business logic functions for podcast job management,
following the existing patterns used in the Podcastfy codebase.
"""

import os
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from ..models import Podcast


def create_podcast_job(db: Session, url: str) -> Podcast:
    """
    Create a new podcast generation job in the database.
    
    Args:
        db: Database session
        url: URL to generate podcast from
        
    Returns:
        Podcast: Newly created podcast job instance
    """
    podcast = Podcast(url=url, status='queued')
    db.add(podcast)
    db.commit()
    db.refresh(podcast)
    return podcast


def get_podcast_by_id(db: Session, podcast_id: str) -> Optional[Podcast]:
    """
    Retrieve podcast by its unique ID.
    
    Args:
        db: Database session
        podcast_id: UUID of the podcast
        
    Returns:
        Podcast: Podcast instance if found, None otherwise
    """
    return db.query(Podcast).filter(Podcast.id == podcast_id).first()


def get_podcast_by_url(db: Session, url: str) -> Optional[Podcast]:
    """
    Retrieve podcast by the source URL.
    
    Args:
        db: Database session  
        url: Source URL of the podcast
        
    Returns:
        Podcast: Podcast instance if found, None otherwise
    """
    return db.query(Podcast).filter(Podcast.url == url).first()


def get_all_podcasts(db: Session, limit: int = 100) -> List[Podcast]:
    """
    Get all podcasts ordered by creation date (newest first).
    
    Args:
        db: Database session
        limit: Maximum number of podcasts to return
        
    Returns:
        List[Podcast]: List of podcast instances
    """
    return db.query(Podcast).order_by(Podcast.created_at.desc()).limit(limit).all()


def get_next_queued_job(db: Session) -> Optional[Podcast]:
    """
    Get the next queued job using FIFO (First In, First Out) ordering.
    
    Args:
        db: Database session
        
    Returns:
        Podcast: Next queued job if available, None otherwise
    """
    return db.query(Podcast).filter_by(status='queued').order_by(Podcast.created_at).first()


def update_podcast_status(db: Session, podcast_id: str, status: str, **kwargs) -> Optional[Podcast]:
    """
    Update podcast status and additional fields.
    
    Args:
        db: Database session
        podcast_id: UUID of the podcast
        status: New status value
        **kwargs: Additional fields to update
        
    Returns:
        Podcast: Updated podcast instance if found, None otherwise
    """
    podcast = get_podcast_by_id(db, podcast_id)
    if podcast:
        podcast.status = status
        for key, value in kwargs.items():
            if hasattr(podcast, key):
                setattr(podcast, key, value)
        db.commit()
        db.refresh(podcast)
    return podcast


def get_existing_audio_path(podcast_id: str) -> Optional[str]:
    """
    Check if audio file exists for podcast using existing naming patterns.
    
    This function checks for audio files following the existing patterns observed
    in the data/audio directory: both UUID-based and truncated UUID patterns.
    
    Args:
        podcast_id: UUID of the podcast
        
    Returns:
        str: Path to existing audio file if found, None otherwise
    """
    # Use existing data/audio directory structure (observed pattern)
    # First try with truncated UUID (16 chars, removing hyphens) 
    audio_path = f"data/audio/podcast_{str(podcast_id).replace('-', '')[:16]}.mp3"
    
    if os.path.exists(audio_path):
        return audio_path
    
    # Also check with full UUID
    audio_path_full = f"data/audio/podcast_{podcast_id}.mp3"
    if os.path.exists(audio_path_full):
        return audio_path_full
    
    # Check with UUID without hyphens (32 chars)
    uuid_no_hyphens = str(podcast_id).replace('-', '')
    audio_path_no_hyphens = f"data/audio/podcast_{uuid_no_hyphens}.mp3"
    if os.path.exists(audio_path_no_hyphens):
        return audio_path_no_hyphens
    
    return None