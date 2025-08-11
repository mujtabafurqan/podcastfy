#!/usr/bin/env python3
"""
Simple test script for Podcastfy
"""

import os
from dotenv import load_dotenv
from podcastfy.client import generate_podcast

def test_podcast_generation():
    """Test podcast generation with a simple URL"""
    
    # Load environment variables
    load_dotenv()
    
    # Check if required API keys are set
    required_keys = ['GEMINI_API_KEY']  # Since we're using Gemini 2.5 Pro
    
    missing_keys = []
    for key in required_keys:
        if not os.getenv(key):
            missing_keys.append(key)
    
    if missing_keys:
        print(f"❌ Missing API keys: {missing_keys}")
        print("Please add them to your .env file:")
        for key in missing_keys:
            print(f"  {key}=your_api_key_here")
        return None
    
    print("✅ API keys found")
    print("📝 Current config: Using Gemini 2.5 Pro")
    
    # Test with a simple website
    test_url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
    
    try:
        print(f"🎙️ Generating podcast from: {test_url}")
        print("⏳ This may take a few minutes...")
        
        # Generate only transcript first (faster test)
        result = generate_podcast(
            urls=[test_url],
            transcript_only=True,  # Skip audio generation for quick test
            llm_model_name="gemini-2.5-pro"
        )
        
        if result:
            print(f"✅ Success! Transcript saved to: {result}")
            return result
        else:
            print("❌ No result returned")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    result = test_podcast_generation()
    if result:
        print(f"\n🎉 Test completed successfully!")
        print(f"📄 Check the transcript at: {result}")
    else:
        print(f"\n❌ Test failed")