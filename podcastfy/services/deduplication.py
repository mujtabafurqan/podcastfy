"""
URL deduplication logic for podcast generation.

This module provides deduplication services to avoid regenerating podcasts
for URLs that have already been processed, following efficiency patterns
observed in the existing codebase.
"""

from typing import Dict, Any
from sqlalchemy.orm import Session
from .podcast_service import get_podcast_by_url


def check_existing_podcast(db: Session, url: str) -> Dict[str, Any]:
    """
    Check if podcast already exists and return appropriate response.
    
    This function implements smart deduplication logic:
    - Returns completed podcasts immediately
    - Returns in-progress jobs for polling
    - Allows retry of failed jobs
    
    Args:
        db: Database session
        url: URL to check for existing podcast
    
    Returns:
        dict: Dictionary containing:
            - exists: Boolean indicating if podcast exists
            - podcast: Podcast instance if exists
            - response: API response data if exists and should be returned
    """
    existing = get_podcast_by_url(db, url)
    
    if not existing:
        return {"exists": False, "podcast": None}
    
    if existing.status == "completed":
        return {
            "exists": True,
            "podcast": existing,
            "response": {
                "job_id": str(existing.id),
                "status": "completed",
                "audio_url": f"/api/audio/{existing.id}"
            }
        }
    elif existing.status in ["queued", "processing"]:
        return {
            "exists": True,
            "podcast": existing,
            "response": {
                "job_id": str(existing.id),
                "status": existing.status
            }
        }
    else:  # failed status - allow retry
        return {"exists": False, "podcast": existing}