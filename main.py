import asyncio
import os
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


@dataclass
class ConversationHistory:
    """Store conversation history for memory"""
    messages: List[Dict[str, Any]]
    
    def add_message(self, role: str, content: str, timestamp: datetime | None = None):
        if timestamp is None:
            timestamp = datetime.now()
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": timestamp.isoformat()
        })
    
    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent messages for context"""
        return self.messages[-limit:]
    
    def get_formatted_history(self, limit: int = 5) -> str:
        """Format recent conversation history for the AI context"""
        recent = self.get_recent_messages(limit)
        formatted = []
        for msg in recent:
            formatted.append(f"{msg['role']}: {msg['content']}")
        return "\n".join(formatted)


# Initialize conversation history
conversation_history = ConversationHistory(messages=[])


# Dummy tool function
def dummy_tool(query: str) -> str:
    """
    A dummy tool that returns a fixed response with the input query.
    In a real app, this could be a weather API, database query, etc.
    Returns a simple string instead of complex structured data.
    """
    return f"🔧 Dummy tool activated! Received query: '{query}'. This is a test response generated at {datetime.now().strftime('%H:%M:%S')}."


# Set up the pydantic-ai agent
def create_agent() -> Agent:
    """Create and configure the pydantic-ai agent"""
    
    # Get model and API key from environment
    model_name = os.getenv("AI_MODEL", "gemini-2.5-flash-lite")
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    # Create the agent with the dummy tool
    agent = Agent(
        model_name,
        system_prompt="""You are a helpful AI assistant with memory of our conversation and access to tools.
        
        You have access to a dummy tool that you can use when the user asks for information that might require external data.
        
        Remember our conversation history and refer to it when relevant. Be conversational and helpful.
        
        When using tools, explain what you're doing and why.""",
        tools=[dummy_tool],
    )
    
    return agent


async def chat_loop():
    """Main chat loop for the terminal application"""
    print("🪶 Guillemot chat framework")
    print("=" * 40)
    print("Type 'quit', 'exit', or 'bye' to end the conversation")
    print("Type 'history' to see recent conversation history")
    print("Type 'clear' to clear conversation history")
    print("=" * 40)
    
    agent = create_agent()
    
    while True:
        try:
            # Get user input
            user_input = input("\n💬 You: ").strip()
            
            # Handle special commands
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() == 'history':
                print("\n📜 Recent Conversation History:")
                print("-" * 30)
                recent_messages = conversation_history.get_recent_messages(10)
                for msg in recent_messages:
                    role_emoji = "💬" if msg["role"] == "user" else "🤖"
                    print(f"{role_emoji} {msg['role']}: {msg['content']}")
                continue
            
            if user_input.lower() == 'clear':
                conversation_history.messages.clear()
                print("\n🧹 Conversation history cleared!")
                continue
            
            if not user_input:
                continue
            
            # Add user message to history
            conversation_history.add_message("user", user_input)
            
            # Prepare context with conversation history
            history_context = conversation_history.get_formatted_history(5)
            
            # Create the prompt with history context
            full_prompt = f"""
            Recent conversation history:
            {history_context}
            
            Current user message: {user_input}
            """
            
            print("\n🤖 Assistant: ", end="", flush=True)
            
            # Run the agent
            result = await agent.run(full_prompt)
            
            # Print the response
            response_text = result.output
            print(response_text)
            
            # Add assistant response to history
            conversation_history.add_message("assistant", response_text)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again or type 'quit' to exit.")


async def main():
    """Main entry point"""
    try:
        await chat_loop()
    except Exception as e:
        print(f"❌ Failed to start chat application: {e}")
        print("Please check your .env file and ensure GEMINI_API_KEY is set correctly.")


if __name__ == "__main__":
    asyncio.run(main())
