#!/usr/bin/env python3
"""
Railway-optimized worker service for Podcastfy.
Standalone script that runs the background job processor.
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment
os.environ.setdefault("PYTHONPATH", str(project_root))

try:
    # Import podcastfy components
    from podcastfy.client import generate_podcast
    from podcastfy.database import get_db_session
    from podcastfy.models import Podcast
    from podcastfy.services.podcast_service import (
        get_next_queued_job, update_podcast_status, get_podcast_by_id
    )
    from podcastfy.utils.logger import setup_logger
    
    # Setup logging
    logger = setup_logger(__name__)
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("📁 Python path:", sys.path)
    print("📂 Current dir:", os.getcwd())
    sys.exit(1)


def extract_title_from_url(url: str) -> str:
    """Extract a basic title from URL for podcast identification."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        path_parts = [p for p in parsed.path.split('/') if p]
        
        if path_parts:
            title_base = path_parts[-1].replace('-', ' ').replace('_', ' ').title()
            return f"{title_base} - {domain}"
        else:
            return f"Podcast from {domain}"
    except Exception:
        return "Generated Podcast"


async def process_podcast_job(podcast_id: str):
    """Process a single podcast generation job."""
    logger.info(f"🎬 Starting job {podcast_id}")
    
    with get_db_session() as db:
        podcast = get_podcast_by_id(db, podcast_id)
        if not podcast:
            logger.error(f"❌ Job {podcast_id} not found")
            return
        
        # Mark as processing
        update_podcast_status(
            db, 
            podcast_id, 
            "processing", 
            started_at=datetime.utcnow()
        )
        logger.info(f"⚡ Processing job {podcast_id}: {podcast.url}")
    
    try:
        # Generate podcast
        audio_path = generate_podcast(
            urls=[podcast.url],
            transcript_only=False,
            llm_model_name="gpt-4o",  # Use reliable model
            api_key_label="OPENAI_API_KEY",
            tts_model="openai"
        )
        
        if not audio_path or not os.path.exists(audio_path):
            raise Exception("Audio generation failed - no output file")
        
        # Update database
        filename = os.path.basename(audio_path)
        
        with get_db_session() as db:
            title = extract_title_from_url(podcast.url)
            
            # Calculate duration
            duration = None
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_mp3(audio_path)
                duration = len(audio) // 1000
            except Exception as e:
                logger.warning(f"⚠️ Duration calculation failed: {e}")
            
            update_podcast_status(
                db,
                podcast_id,
                "completed",
                completed_at=datetime.utcnow(),
                audio_filename=filename,
                title=title,
                duration=duration
            )
        
        logger.info(f"✅ Job {podcast_id} completed: {audio_path}")
        
    except Exception as e:
        logger.error(f"❌ Job {podcast_id} failed: {str(e)}")
        
        with get_db_session() as db:
            podcast_obj = get_podcast_by_id(db, podcast_id)
            retry_count = podcast_obj.retry_count + 1 if podcast_obj else 1
            
            update_podcast_status(
                db,
                podcast_id,
                "failed",
                completed_at=datetime.utcnow(),
                error_message=str(e)[:500],
                retry_count=retry_count
            )


async def worker_main_loop():
    """Main worker loop."""
    logger.info("🎙️ Podcastfy Worker started - polling for jobs...")
    
    consecutive_empty_polls = 0
    
    while True:
        try:
            with get_db_session() as db:
                job = get_next_queued_job(db)
                
                if job:
                    consecutive_empty_polls = 0
                    await process_podcast_job(str(job.id))
                else:
                    consecutive_empty_polls += 1
                    
                    if consecutive_empty_polls % 12 == 0:
                        logger.info("⏳ No jobs in queue, waiting...")
                    
                    await asyncio.sleep(5)
                    
        except Exception as e:
            logger.error(f"❌ Worker error: {str(e)}")
            await asyncio.sleep(10)


if __name__ == "__main__":
    try:
        print("🚀 Starting Podcastfy Worker...")
        asyncio.run(worker_main_loop())
    except KeyboardInterrupt:
        print("🛑 Worker stopped")
    except Exception as e:
        print(f"💥 Worker crashed: {e}")
        sys.exit(1)