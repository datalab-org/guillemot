#!/usr/bin/env python3
"""Test script to understand pydantic-ai API"""

import asyncio
import os
from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv()

async def test_agent():
    model_name = os.getenv("AI_MODEL", "gemini-2.5-flash-lite")
    agent = Agent(model_name)
    
    result = await agent.run("Say hello")
    
    print(f"Result type: {type(result)}")
    print(f"Result attributes: {dir(result)}")
    print(f"Result: {result}")
    
    # Try different ways to access the response
    if hasattr(result, 'data'):
        print(f"result.data: {result.data}")
    if hasattr(result, 'content'):
        print(f"result.content: {result.content}")
    if hasattr(result, 'message'):
        print(f"result.message: {result.message}")

if __name__ == "__main__":
    asyncio.run(test_agent())
