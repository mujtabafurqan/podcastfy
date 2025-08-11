"""
Simple integration test for async API functionality.

This is a streamlined version following the guide pattern but with
improvements based on existing codebase patterns.
"""

import requests
import time
import json
import sys

# Configuration following existing patterns
BASE_URL = "http://localhost:8001"
TEST_URL = "https://en.wikipedia.org/wiki/Artificial_intelligence"


def test_async_flow():
    """Test the complete async flow following the guide structure."""
    
    print("🧪 Testing Podcastfy Async API Flow")
    print("=" * 45)
    
    try:
        # 1. Test health check
        print("\n1️⃣ Testing health check...")
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        response.raise_for_status()
        health_data = response.json()
        print(f"✅ Health: {health_data}")
        
        # 2. Test library (should show existing podcasts if migrated)
        print("\n2️⃣ Getting current library...")
        response = requests.get(f"{BASE_URL}/api/library", timeout=10)
        response.raise_for_status()
        library = response.json()
        print(f"📚 Current library has {len(library)} podcasts")
        
        # 3. Submit new job
        print("\n3️⃣ Submitting new job...")
        response = requests.post(
            f"{BASE_URL}/api/generate-async",
            json={"url": TEST_URL},
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        job_id = result["job_id"]
        print(f"📝 Job created: {job_id}")
        print(f"📊 Initial status: {result['status']}")
        
        # 4. Poll for status
        print("\n4️⃣ Polling for completion...")
        max_polls = 60  # 5 minutes max
        poll_count = 0
        
        while poll_count < max_polls:
            try:
                response = requests.get(f"{BASE_URL}/api/status/{job_id}", timeout=10)
                response.raise_for_status()
                status_data = response.json()
                
                print(f"⏳ Poll {poll_count + 1}/{max_polls}: {status_data['status']}")
                
                if status_data["status"] == "completed":
                    print("✅ Job completed successfully!")
                    audio_url = status_data.get('audio_url')
                    if audio_url:
                        print(f"🎵 Audio URL: {audio_url}")
                    break
                elif status_data["status"] == "failed":
                    error_msg = status_data.get('error_message', 'Unknown error')
                    print(f"❌ Job failed: {error_msg}")
                    return False
                
                time.sleep(5)
                poll_count += 1
                
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Status check failed: {e}")
                time.sleep(5)
                poll_count += 1
        
        if poll_count >= max_polls:
            print("⏰ Job timed out - may still be processing")
        
        # 5. Check updated library
        print("\n5️⃣ Checking updated library...")
        response = requests.get(f"{BASE_URL}/api/library", timeout=10)
        response.raise_for_status()
        new_library = response.json()
        print(f"📈 Library now has {len(new_library)} podcasts")
        
        print("\n🎉 Test flow completed successfully!")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        print("💡 Make sure the async API server is running on localhost:8001")
        return False
    except (KeyError, json.JSONDecodeError) as e:
        print(f"❌ Response format error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    """Main entry point with proper exit codes."""
    try:
        success = test_async_flow()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()