"""
Background worker for processing podcast generation jobs.

This polls PostgreSQL for queued jobs and uses the existing
podcastfy.client.generate_podcast function to maintain compatibility
with existing patterns and configurations.
"""

import os
import sys
import asyncio
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path

# Import existing podcastfy functionality following existing patterns
from .client import generate_podcast
from .database import get_db_session
from .models import Podcast
from .services.podcast_service import (
    get_next_queued_job, update_podcast_status, get_podcast_by_id
)
from .utils.config import load_config
from .utils.config_conversation import load_conversation_config
from .utils.logger import setup_logger

# Configure logging using existing patterns
logger = setup_logger(__name__)


def extract_title_from_url(url: str) -> str:
    """
    Extract a basic title from URL for podcast identification.
    
    Args:
        url: The source URL
        
    Returns:
        str: Generated title based on URL structure
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        path_parts = [p for p in parsed.path.split('/') if p]
        
        if path_parts:
            # Use last path segment as title base
            title_base = path_parts[-1].replace('-', ' ').replace('_', ' ').title()
            return f"{title_base} - {domain}"
        else:
            return f"Podcast from {domain}"
    except Exception:
        return "Generated Podcast"


async def process_podcast_job(podcast_id: str):
    """
    Process a single podcast generation job using existing infrastructure.
    
    Args:
        podcast_id: UUID of the podcast job to process
    """
    logger.info(f"Starting to process job {podcast_id}")
    
    # Get the podcast details and mark as processing
    with get_db_session() as db:
        podcast = get_podcast_by_id(db, podcast_id)
        if not podcast:
            logger.error(f"Job {podcast_id} not found in database")
            return
        
        # Capture URL while session is active
        podcast_url = podcast.url
        
        # Mark as processing
        update_podcast_status(
            db, 
            podcast_id, 
            "processing", 
            started_at=datetime.utcnow()
        )
        
        logger.info(f"Marked job {podcast_id} as processing for URL: {podcast_url}")
    
    try:
        # Load existing configuration to use current settings
        config = load_config()
        conversation_config = load_conversation_config()
        
        # Get LLM model from existing config (should be gpt-5 based on config.yaml)
        llm_model = config.get('llm_model', 'gpt-5')
        
        logger.info(f"Generating podcast for URL: {podcast_url}")
        logger.info(f"Using LLM model: {llm_model}")
        
        # Use existing generate_podcast function with current settings
        # This ensures compatibility with existing conversation_config.yaml
        audio_path = generate_podcast(
            urls=[podcast_url],
            transcript_only=False,
            llm_model_name=llm_model,
            api_key_label="OPENAI_API_KEY",
            tts_model="openai",
            config=config.config if hasattr(config, 'config') else None,
            conversation_config=conversation_config.to_dict() if hasattr(conversation_config, 'to_dict') else None
        )
        
        if not audio_path or not os.path.exists(audio_path):
            raise Exception("Audio generation failed - no output file produced")
        
        # Upload to Cloudflare R2 storage
        filename = os.path.basename(audio_path)
        
        try:
            from .utils.r2_storage import get_r2_storage
            r2_storage = get_r2_storage()
            
            # Upload to R2 with the same filename
            public_url = r2_storage.upload_audio_file(audio_path, filename)
            logger.info(f"Audio uploaded to R2: {public_url}")
            
            # Store the R2 URL for later use
            audio_url = public_url
            
        except Exception as r2_error:
            logger.error(f"Failed to upload to R2 storage: {r2_error}")
            raise Exception(f"Audio generation completed but R2 upload failed: {r2_error}")
        
        logger.info(f"Audio saved locally: {audio_path}")
        logger.info(f"Audio available at: {audio_url}")
        
        # Update database with completion
        with get_db_session() as db:
            title = extract_title_from_url(podcast_url)
            
            # Calculate duration if possible using pydub (available in requirements)
            duration = None
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_mp3(audio_path)
                duration = len(audio) // 1000  # Convert to seconds
                logger.info(f"Audio duration calculated: {duration} seconds")
            except ImportError:
                logger.warning("pydub not available for duration calculation")
            except Exception as e:
                logger.warning(f"Could not calculate audio duration: {e}")
            
            # Store both filename and R2 URL
            update_podcast_status(
                db,
                podcast_id,
                "completed",
                completed_at=datetime.utcnow(),
                audio_filename=filename,
                audio_url=audio_url,
                title=title,
                duration=duration
            )
        
        logger.info(f"Job {podcast_id} completed successfully")
        logger.info(f"Audio saved to: {audio_path}")
        
    except Exception as e:
        logger.error(f"Job {podcast_id} failed: {str(e)}")
        
        with get_db_session() as db:
            podcast_obj = get_podcast_by_id(db, podcast_id)
            if podcast_obj:
                current_retry_count = podcast_obj.retry_count
                retry_count = current_retry_count + 1
            else:
                retry_count = 1
            
            update_podcast_status(
                db,
                podcast_id,
                "failed",
                completed_at=datetime.utcnow(),
                error_message=str(e)[:500],  # Limit error message length
                retry_count=retry_count
            )


async def worker_main_loop():
    """
    Main worker loop that polls for queued jobs using existing patterns.
    
    This function runs continuously, polling the database for new jobs
    and processing them using the existing podcast generation pipeline.
    """
    logger.info("🎙️  Podcastfy Worker started - polling for jobs...")
    logger.info("Using existing data/audio directory for storage")
    logger.info("Using existing conversation_config.yaml settings")
    
    consecutive_empty_polls = 0
    
    while True:
        try:
            with get_db_session() as db:
                # Get next queued job (FIFO - First In, First Out)
                job = get_next_queued_job(db)
                
                if job:
                    consecutive_empty_polls = 0
                    # Capture values while session is active
                    job_id = str(job.id)
                    job_url = job.url
                    logger.info(f"📝 Found job {job_id} for URL: {job_url}")
                    await process_podcast_job(job_id)
                else:
                    consecutive_empty_polls += 1
                    
                    # Log every 12 polls (1 minute at 5-second intervals) when no jobs
                    if consecutive_empty_polls % 12 == 0:
                        logger.info("⏳ No jobs in queue, waiting for new submissions...")
                    
                    # Wait 5 seconds before next poll
                    await asyncio.sleep(5)
                    
        except KeyboardInterrupt:
            logger.info("🛑 Worker interrupted by user")
            break
        except Exception as e:
            logger.error(f"❌ Worker error: {str(e)}")
            # Wait longer on error to avoid tight error loops
            await asyncio.sleep(10)


def main():
    """
    Main entry point for the worker process.
    
    This function handles the async event loop and graceful shutdown.
    """
    try:
        # Verify database connection before starting
        logger.info("🔧 Verifying database connection...")
        with get_db_session() as db:
            # Simple connection test
            pass
        logger.info("✅ Database connection verified")
        
        # Start the main worker loop
        asyncio.run(worker_main_loop())
        
    except KeyboardInterrupt:
        logger.info("🛑 Worker stopped by user")
    except Exception as e:
        logger.error(f"💥 Worker crashed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()