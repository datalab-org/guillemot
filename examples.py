#!/usr/bin/env python3
"""
Example: Extending Guillemot with Additional Tools

This file demonstrates how to add new tools to the Guillemot LLM chat app.
You can copy and modify these examples to create your own tools.
"""

import asyncio
import os
import json
import random
from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel
from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv()

# Example tool models
class WeatherResult(BaseModel):
    """Mock weather tool result"""
    location: str
    temperature: int
    condition: str
    timestamp: str

class CalculatorResult(BaseModel):
    """Calculator tool result"""
    expression: str
    result: float
    timestamp: str

class FactResult(BaseModel):
    """Random fact tool result"""
    category: str
    fact: str
    source: str
    timestamp: str

# Example tool functions
def mock_weather_tool(location: str) -> WeatherResult:
    """
    Mock weather tool - returns fake weather data.
    In a real app, this would call a weather API.
    """
    conditions = ["sunny", "cloudy", "rainy", "snowy", "foggy"]
    temperature = random.randint(-10, 35)
    condition = random.choice(conditions)
    
    return WeatherResult(
        location=location,
        temperature=temperature,
        condition=condition,
        timestamp=datetime.now().isoformat()
    )

def calculator_tool(expression: str) -> CalculatorResult:
    """
    Simple calculator tool - evaluates basic math expressions.
    Note: In production, use a proper math parser for security.
    """
    try:
        # Only allow basic math operations for security
        allowed_chars = set('0123456789+-*/.()')
        if not set(expression).issubset(allowed_chars):
            raise ValueError("Invalid characters in expression")
        
        result = eval(expression)
        
        return CalculatorResult(
            expression=expression,
            result=float(result),
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        return CalculatorResult(
            expression=expression,
            result=float('nan'),
            timestamp=datetime.now().isoformat()
        )

def random_fact_tool(category: str = "general") -> FactResult:
    """
    Random fact tool - returns interesting facts.
    In a real app, this could query a facts database or API.
    """
    facts_db = {
        "science": [
            "A single cloud can weigh more than a million pounds",
            "There are more possible games of chess than atoms in the observable universe",
            "Honey never spoils - archaeologists have found edible honey in ancient Egyptian tombs"
        ],
        "animals": [
            "Octopuses have three hearts and blue blood",
            "A shrimp's heart is located in its head",
            "Elephants are afraid of bees and will change their migration routes to avoid them"
        ],
        "general": [
            "The shortest war in history lasted only 38-45 minutes",
            "Bananas are berries, but strawberries aren't",
            "A group of flamingos is called a 'flamboyance'"
        ]
    }
    
    category_facts = facts_db.get(category.lower(), facts_db["general"])
    fact = random.choice(category_facts)
    
    return FactResult(
        category=category,
        fact=fact,
        source="Guillemot Fact Database",
        timestamp=datetime.now().isoformat()
    )

def create_extended_agent() -> Agent:
    """Create an agent with multiple tools"""
    model_name = os.getenv("AI_MODEL", "gemini-2.5-flash-lite")
    
    agent = Agent(
        model_name,
        system_prompt="""You are a helpful AI assistant with access to several tools:

1. mock_weather_tool(location) - Get weather information for a location
2. calculator_tool(expression) - Perform mathematical calculations
3. random_fact_tool(category) - Get random facts (categories: science, animals, general)

Use these tools when appropriate to help users. Always explain what tool you're using and why.
Be conversational and helpful in your responses.""",
        tools=[mock_weather_tool, calculator_tool, random_fact_tool],
    )
    
    return agent

async def demo_extended_tools():
    """Demonstrate the extended tools"""
    print("🔧 Guillemot Extended Tools Demo")
    print("=" * 40)
    
    agent = create_extended_agent()
    
    # Test queries that should trigger different tools
    test_queries = [
        "What's the weather like in Paris?",
        "Calculate 15 * 42 + 7",
        "Tell me an interesting animal fact",
        "What's 2^10?",
        "Give me a science fact"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        print("-" * 30)
        
        try:
            result = await agent.run(query)
            print(f"🤖 Response: {result.output}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()

if __name__ == "__main__":
    print("This is a demo of extended tools for Guillemot.")
    print("To use these tools in the main app, copy the tool functions")
    print("and add them to the agent in main.py")
    print()
    
    # Run the demo
    asyncio.run(demo_extended_tools())
