"""
Async FastAPI extension for Podcastfy UI.

This extends the existing fast_app.py with job queue capabilities
while maintaining backward compatibility with existing patterns.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path
import uvicorn

# Import existing functionality to maintain compatibility
from .fast_app import load_base_config, merge_configs

# Import new database functionality
from ..database import get_db, create_tables
from ..models import Podcast
from ..services.podcast_service import (
    create_podcast_job, get_podcast_by_id, get_all_podcasts,
    get_existing_audio_path
)
from ..services.deduplication import check_existing_podcast
from ..utils.logger import setup_logger

# Configure logging using existing pattern
logger = setup_logger(__name__)

# Lifespan event handler (replaces deprecated on_event startup)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifespan events."""
    # Startup
    try:
        create_tables()
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    
    yield
    
    # Shutdown (cleanup if needed)
    logger.info("Application shutdown")

# Create new app instance following existing pattern
app = FastAPI(
    title="Podcastfy Async API", 
    version="1.0.0",
    description="Async job processing API for Podcastfy UI",
    lifespan=lifespan
)

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js development server
        "http://127.0.0.1:3000",  # Alternative localhost
        "https://speakeasy-ui.vercel.app",  # Production frontend (adjust as needed)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Pydantic models for API (following existing typing patterns)
class GenerateAsyncRequest(BaseModel):
    """Request model for async podcast generation."""
    url: str = Field(..., description="URL to generate podcast from")

class GenerateAsyncResponse(BaseModel):
    """Response model for async podcast generation request."""
    job_id: str
    status: str
    audio_url: Optional[str] = None

class StatusResponse(BaseModel):
    """Response model for job status queries."""
    status: str
    audio_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

class PodcastResponse(BaseModel):
    """Response model for podcast library items."""
    id: str
    url: str
    title: Optional[str] = None
    audio_url: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    duration: Optional[int] = None

# API Endpoints following existing patterns
@app.post("/api/generate-async", response_model=GenerateAsyncResponse)
async def generate_podcast_async(
    request: GenerateAsyncRequest, 
    db: Session = Depends(get_db)
):
    """
    Submit URL for async podcast generation.
    Returns immediately with job_id for status polling.
    """
    try:
        # Check for existing podcast (deduplication)
        result = check_existing_podcast(db, request.url)
        
        if result["exists"]:
            response_data = result["response"]
            return GenerateAsyncResponse(**response_data)
        
        # Create new podcast job
        podcast = create_podcast_job(db, request.url)
        
        logger.info(f"Created new job {podcast.id} for URL: {request.url}")
        
        return GenerateAsyncResponse(
            job_id=str(podcast.id),
            status=podcast.status
        )
        
    except Exception as e:
        logger.error(f"Error creating async job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status/{job_id}", response_model=StatusResponse)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get the status of a podcast generation job."""
    
    podcast = get_podcast_by_id(db, job_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Job not found")
    
    response = StatusResponse(
        status=podcast.status,
        error_message=podcast.error_message,
        created_at=podcast.created_at.isoformat() if podcast.created_at else None,
        started_at=podcast.started_at.isoformat() if podcast.started_at else None,
        completed_at=podcast.completed_at.isoformat() if podcast.completed_at else None,
    )
    
    if podcast.status == "completed":
        response.audio_url = f"/api/audio/{job_id}"
    
    return response

@app.get("/api/library", response_model=List[PodcastResponse])
async def get_podcast_library(db: Session = Depends(get_db)):
    """Get all podcasts in the library."""
    
    try:
        podcasts = get_all_podcasts(db, limit=100)
        return [PodcastResponse(**podcast.to_dict()) for podcast in podcasts]
        
    except Exception as e:
        logger.error(f"Error fetching library: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audio/{podcast_id}")
async def serve_audio_file(podcast_id: str, db: Session = Depends(get_db)):
    """Serve audio file for completed podcast."""
    
    podcast = get_podcast_by_id(db, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    
    if podcast.status != "completed":
        raise HTTPException(status_code=404, detail="Audio not ready")
    
    # Use the audio_filename stored in database if available
    if podcast.audio_filename:
        audio_path = f"data/audio/{podcast.audio_filename}"
        if os.path.exists(audio_path):
            return FileResponse(
                audio_path,
                media_type="audio/mpeg",
                filename=f"{podcast.title or 'podcast'}.mp3"
            )
    
    # Fallback: try to find file using existing patterns
    audio_path = get_existing_audio_path(str(podcast.id))
    if not audio_path or not os.path.exists(audio_path):
        logger.error(f"Audio file not found for podcast {podcast_id}. Expected: {podcast.audio_filename}")
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename=f"{podcast.title or 'podcast'}.mp3"
    )

@app.get("/api/health")
async def health_check():
    """Health check endpoint following existing pattern."""
    return {"status": "healthy", "service": "podcastfy-async"}

# Development server following existing pattern from fast_app.py
if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8001))
    # Use import string for reload mode to avoid warnings
    uvicorn.run("podcastfy.api.async_app:app", host=host, port=port, reload=True)