"""
Integration test script for async API functionality.

This module provides comprehensive testing of the async podcast generation
API, following existing test patterns while providing practical integration
testing capabilities.
"""

import requests
import time
import json
import sys
import os
from typing import Dict, Any, Optional
from urllib.parse import urljoin

# Use existing logging patterns
from .utils.logger import setup_logger

# Configure logging following existing patterns
logger = setup_logger(__name__)

# Test configuration following existing patterns
TEST_CONFIG = {
    "base_url": "http://localhost:8001",
    "timeout": 10,  # seconds
    "max_polls": 60,  # 5 minutes max for job completion
    "poll_interval": 5,  # seconds between status checks
}

# Test URLs following existing test patterns (similar to test_client.py)
TEST_URLS = [
    "https://en.wikipedia.org/wiki/Jim_Lovell",
]


class AsyncAPITester:
    """
    Integration tester for Podcastfy Async API.
    
    This class provides comprehensive testing capabilities for the async
    podcast generation API, following existing code patterns.
    """
    
    def __init__(self, base_url: str = None):
        """
        Initialize the API tester.
        
        Args:
            base_url: Base URL for the API (defaults to localhost:8001)
        """
        self.base_url = base_url or TEST_CONFIG["base_url"]
        self.session = requests.Session()
        self.session.timeout = TEST_CONFIG["timeout"]
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[requests.Response]:
        """
        Make HTTP request with proper error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object or None if request failed
        """
        url = urljoin(self.base_url, endpoint)
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {method} {url}: {str(e)}")
            return None
    
    def test_health_check(self) -> bool:
        """Test API health check endpoint."""
        logger.info("🔍 Testing health check...")
        
        response = self._make_request("GET", "/api/health")
        if not response:
            return False
            
        try:
            health_data = response.json()
            logger.info(f"Health check response: {health_data}")
            
            # Validate expected health response structure
            if health_data.get("status") == "healthy":
                logger.info("✅ Health check passed")
                return True
            else:
                logger.error(f"❌ Unexpected health status: {health_data}")
                return False
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON response: {str(e)}")
            return False
    
    def test_library_endpoint(self) -> Optional[int]:
        """
        Test library endpoint and return podcast count.
        
        Returns:
            Number of podcasts in library, or None if test failed
        """
        logger.info("📚 Testing library endpoint...")
        
        response = self._make_request("GET", "/api/library")
        if not response:
            return None
            
        try:
            library = response.json()
            count = len(library)
            logger.info(f"Current library has {count} podcasts")
            
            # Validate library structure if podcasts exist
            if count > 0 and isinstance(library[0], dict):
                required_fields = ["id", "url", "status"]
                if all(field in library[0] for field in required_fields):
                    logger.info("✅ Library structure is valid")
                else:
                    logger.warning("⚠️ Library items missing required fields")
            
            return count
            
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"❌ Invalid library response: {str(e)}")
            return None
    
    def submit_podcast_job(self, url: str) -> Optional[str]:
        """
        Submit new podcast job and return job ID.
        
        Args:
            url: URL to generate podcast from
            
        Returns:
            Job ID if successful, None otherwise
        """
        logger.info(f"📝 Submitting job for URL: {url}")
        
        payload = {"url": url}
        response = self._make_request("POST", "/api/generate-async", json=payload)
        if not response:
            return None
            
        try:
            result = response.json()
            job_id = result.get("job_id")
            status = result.get("status")
            
            if job_id:
                logger.info(f"✅ Job created: {job_id}")
                logger.info(f"Initial status: {status}")
                return job_id
            else:
                logger.error(f"❌ No job_id in response: {result}")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid job submission response: {str(e)}")
            return None
    
    def poll_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Poll job status until completion or timeout.
        
        Args:
            job_id: Job ID to monitor
            
        Returns:
            Final status data or None if failed
        """
        logger.info(f"⏳ Polling job status for {job_id}...")
        
        max_polls = TEST_CONFIG["max_polls"]
        poll_interval = TEST_CONFIG["poll_interval"]
        
        for poll_count in range(1, max_polls + 1):
            response = self._make_request("GET", f"/api/status/{job_id}")
            if not response:
                continue
                
            try:
                status_data = response.json()
                current_status = status_data.get("status", "unknown")
                
                logger.info(f"Poll {poll_count}/{max_polls}: {current_status}")
                
                # Check for completion states
                if current_status == "completed":
                    audio_url = status_data.get("audio_url")
                    logger.info(f"✅ Job completed successfully!")
                    if audio_url:
                        logger.info(f"🎵 Audio URL: {audio_url}")
                    return status_data
                    
                elif current_status == "failed":
                    error_msg = status_data.get("error_message", "Unknown error")
                    logger.error(f"❌ Job failed: {error_msg}")
                    return status_data
                    
                # Still processing, wait and continue
                time.sleep(poll_interval)
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid status response: {str(e)}")
                time.sleep(poll_interval)
        
        logger.error(f"⏰ Job {job_id} timed out after {max_polls} polls")
        return None
    
    def test_deduplication(self, url: str) -> bool:
        """
        Test URL deduplication by submitting the same URL twice.
        
        Args:
            url: URL to test with
            
        Returns:
            True if deduplication works correctly
        """
        logger.info(f"🔄 Testing deduplication with URL: {url}")
        
        # Submit first job
        job_id_1 = self.submit_podcast_job(url)
        if not job_id_1:
            return False
            
        # Submit same URL again (should return existing job)
        job_id_2 = self.submit_podcast_job(url)
        if not job_id_2:
            return False
            
        if job_id_1 == job_id_2:
            logger.info("✅ Deduplication working - same job ID returned")
            return True
        else:
            logger.warning(f"⚠️ Different job IDs: {job_id_1} vs {job_id_2}")
            return False


def run_comprehensive_test() -> bool:
    """
    Run comprehensive async API test following existing patterns.
    
    Returns:
        True if all tests pass, False otherwise
    """
    logger.info("🧪 Starting Comprehensive Async API Test Suite")
    logger.info("=" * 50)
    
    tester = AsyncAPITester()
    test_results = []
    
    # Test 1: Health Check
    logger.info("\n1️⃣ HEALTH CHECK TEST")
    health_result = tester.test_health_check()
    test_results.append(("Health Check", health_result))
    
    if not health_result:
        logger.error("❌ Health check failed - aborting remaining tests")
        return False
    
    # Test 2: Library Endpoint
    logger.info("\n2️⃣ LIBRARY ENDPOINT TEST")
    initial_count = tester.test_library_endpoint()
    test_results.append(("Library Endpoint", initial_count is not None))
    
    if initial_count is not None:
        logger.info(f"📊 Found {initial_count} existing podcasts")
    
    # Test 3: Job Submission and Processing
    logger.info("\n3️⃣ JOB SUBMISSION & PROCESSING TEST")
    test_url = TEST_URLS[0]  # Use first test URL
    job_id = tester.submit_podcast_job(test_url)
    submission_success = job_id is not None
    test_results.append(("Job Submission", submission_success))
    
    if job_id:
        # Test 4: Status Polling
        logger.info("\n4️⃣ STATUS POLLING TEST")
        final_status = tester.poll_job_status(job_id)
        polling_success = final_status is not None
        test_results.append(("Status Polling", polling_success))
        
        # Test 5: Library Update Check
        logger.info("\n5️⃣ LIBRARY UPDATE TEST")
        final_count = tester.test_library_endpoint()
        if initial_count is not None and final_count is not None:
            library_updated = final_count >= initial_count
            test_results.append(("Library Update", library_updated))
            logger.info(f"📈 Library count: {initial_count} → {final_count}")
        
        # Test 6: Deduplication
        logger.info("\n6️⃣ DEDUPLICATION TEST")
        dedup_result = tester.test_deduplication(test_url)
        test_results.append(("Deduplication", dedup_result))
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 TEST RESULTS SUMMARY")
    logger.info("=" * 50)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    total = len(test_results)
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed successfully!")
        return True
    else:
        logger.error(f"😞 {total - passed} tests failed")
        return False


def main():
    """Main entry point for the test script."""
    try:
        success = run_comprehensive_test()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("🛑 Tests interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"💥 Test suite crashed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()