#!/usr/bin/env python3
"""
Test available Gemini models
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

def list_available_models():
    """List available Gemini models"""
    load_dotenv()
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env file")
        return
    
    genai.configure(api_key=api_key)
    
    try:
        print("🔍 Available Gemini models:")
        models = genai.list_models()
        
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                print(f"  ✅ {model.name}")
                
    except Exception as e:
        print(f"❌ Error listing models: {e}")

if __name__ == "__main__":
    list_available_models()