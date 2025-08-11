#!/usr/bin/env python3
"""
Test audio generation with Podcastfy
"""

import os
from dotenv import load_dotenv
from podcastfy.client import generate_podcast

def test_audio_generation():
    """Test full audio generation"""
    
    load_dotenv()
    
    # Test with a shorter article for faster audio generation
    test_url = "https://en.wikipedia.org/wiki/Hurra-yi_Khuttali"
    
    try:
        print(f"🎙️ Generating podcast with audio from: {test_url}")
        print("⏳ This will take longer (includes TTS)...")
        
        # Generate full podcast with audio (using OpenAI TTS by default)
        result = generate_podcast(
            urls=[test_url],
            transcript_only=False,  # Generate audio too
            llm_model_name="gpt-5",
            api_key_label="OPENAI_API_KEY",  # Specify correct API key for GPT-5
            tts_model="openai"  # Use OpenAI TTS (requires OPENAI_API_KEY)
        )
        
        if result:
            print(f"✅ Success! Audio saved to: {result}")
            return result
        else:
            print("❌ No result returned")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    # Check for required API keys
    load_dotenv()
    required_keys = ['GEMINI_API_KEY', 'OPENAI_API_KEY']
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    
    if missing_keys:
        print(f"❌ Missing API keys for audio generation: {missing_keys}")
        print("Add to .env file:")
        for key in missing_keys:
            print(f"  {key}=your_api_key_here")
    else:
        result = test_audio_generation()
        if result:
            print(f"\n🎉 Audio generation completed!")
            print(f"🔊 Play the podcast: {result}")
        else:
            print(f"\n❌ Audio generation failed")