#!/usr/bin/env python3
"""Quick test of the multimodal chat functionality"""

import asyncio
from pathlib import Path
import sys
import os

# Add the current directory to the path so we can import from main.py
sys.path.insert(0, str(Path(__file__).parent))

from main import create_agent
from pydantic_ai import ImageUrl

async def quick_test():
    """Quick test of multimodal functionality in main app"""
    print("🧪 Quick test of Guillemot multimodal functionality...")
    
    try:
        agent = create_agent()
        
        # Test basic text
        print("\n1. Testing basic text chat...")
        result = await agent.run("Hello! Can you introduce yourself briefly?")
        print(f"✅ Text chat works: {result.output[:100]}...")
        
        # Test image analysis
        print("\n2. Testing image analysis...")
        test_image = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/280px-PNG_transparency_demonstration_1.png"
        result = await agent.run([
            "What do you see in this image?",
            ImageUrl(url=test_image)
        ])
        print(f"✅ Image analysis works: {result.output[:100]}...")
        
        print("\n🎉 All tests passed! The application is ready to use.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(quick_test())
    if not success:
        print("\n⚠️  Please check your environment configuration.")
    else:
        print("\n🚀 Ready to run: python main.py")
