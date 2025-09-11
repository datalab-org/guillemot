#!/usr/bin/env python3
"""Simple test of the main app functionality"""

import asyncio
from main import create_agent

async def test_basic_functionality():
    print("🧪 Testing basic agent functionality...")
    agent = create_agent()
    
    # Test basic conversation
    result = await agent.run("Hello! Can you introduce yourself?")
    print(f"✅ Basic chat: {result.output}")
    
    # Test tool usage
    result = await agent.run("Please use the dummy tool to test something")
    print(f"✅ Tool test: {result.output}")

if __name__ == "__main__":
    asyncio.run(test_basic_functionality())
