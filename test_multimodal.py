#!/usr/bin/env python3
"""Test multimodal functionality of Guillemot"""

import asyncio
import os
from pydantic_ai import Agent, ImageUrl
from dotenv import load_dotenv

load_dotenv()

async def test_image_functionality():
    """Test basic image analysis functionality"""
    print("🧪 Testing Guillemot multimodal image functionality...")
    
    model_name = os.getenv("AI_MODEL", "gemini-2.5-flash-lite")
    agent = Agent(model_name)
    
    # Test with a public image URL
    test_image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/280px-PNG_transparency_demonstration_1.png"
    
    print(f"🖼️  Testing with image URL: {test_image_url}")
    
    try:
        result = await agent.run([
            "What do you see in this image? Describe it briefly.",
            ImageUrl(url=test_image_url)
        ])
        print(f"✅ Image analysis result: {result.output}")
        return True
    except Exception as e:
        print(f"❌ Error testing image functionality: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_image_functionality())
    if success:
        print("\n🎉 Multimodal functionality appears to be working!")
        print("You can now use image URLs or local file paths in the chat.")
    else:
        print("\n⚠️  There may be issues with multimodal functionality.")
        print("Check your model configuration and API permissions.")
