import asyncio
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from pydantic_ai import Agent, ImageUrl

from guillemot.utils import load_local_image
from guillemot.tools import (
    get_optimade_cifs,
    plot_refinement_results,
    run_topas_refinement,
    save_topas_inp,
)

# Load environment variables
load_dotenv()

# Configure Logfire if token is available
try:
    import logfire

    logfire_token = os.getenv("LOGFIRE_TOKEN")
    if logfire_token:
        logfire.configure(token=logfire_token)
except ImportError:
    pass  # Logfire is optional


@dataclass
class ConversationHistory:
    """Store conversation history for memory"""

    messages: List[Dict[str, Any]]

    def add_message(
        self,
        role: str,
        content: str,
        has_image: bool = False,
        timestamp: datetime | None = None,
    ):
        if timestamp is None:
            timestamp = datetime.now()
        self.messages.append(
            {
                "role": role,
                "content": content,
                "has_image": has_image,
                "timestamp": timestamp.isoformat(),
            }
        )

    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent messages for context"""
        return self.messages[-limit:]

    def get_formatted_history(self, limit: int = 5) -> str:
        """Format recent conversation history for the AI context"""
        recent = self.get_recent_messages(limit)
        formatted = []
        for msg in recent:
            content = msg["content"]
            if msg.get("has_image", False):
                content += " [included an image]"
            formatted.append(f"{msg['role']}: {content}")
        return "\n".join(formatted)


# Initialize conversation history
conversation_history = ConversationHistory(messages=[])


def is_image_url(text: str) -> bool:
    """Check if text contains an image URL"""
    url_pattern = r"https?://[^\s]+\.(jpg|jpeg|png|gif|bmp|webp)"
    return bool(re.search(url_pattern, text, re.IGNORECASE))


def extract_image_url(text: str) -> tuple[str, str]:
    """Extract image URL from text and return (text_without_url, image_url)"""
    url_pattern = r"https?://[^\s]+\.(jpg|jpeg|png|gif|bmp|webp)"
    match = re.search(url_pattern, text, re.IGNORECASE)
    if match:
        image_url = match.group()
        text_without_url = text.replace(image_url, "").strip()
        return text_without_url, image_url
    return text, ""


def is_local_image_path(text: str) -> bool:
    """Check if text contains a local image file path"""
    # Look for file:// URLs or local paths ending with image extensions
    file_pattern = r"(?:file://)?[^\s]+\.(jpg|jpeg|png|gif|bmp|webp)"
    return bool(re.search(file_pattern, text, re.IGNORECASE))


def extract_local_image_path(text: str) -> tuple[str, str]:
    """Extract local image path from text and return (text_without_path, image_path)"""
    file_pattern = r"(?:file://)?([^\s]+\.(jpg|jpeg|png|gif|bmp|webp))"
    match = re.search(file_pattern, text, re.IGNORECASE)
    if match:
        image_path = match.group(1)
        # Remove file:// prefix if present
        image_path = image_path.replace("file://", "")
        text_without_path = text.replace(match.group(), "").strip()
        return text_without_path, image_path
    return text, ""


# Set up the pydantic-ai agent
def create_agent() -> Agent:
    """Create and configure the pydantic-ai agent"""

    # Get model and API key from environment
    model_name = os.getenv("GUILLEMOT_AI_MODEL", "gemini-2.5-flash-lite")
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")

    with open("examples/NaCoO2/example_refinement_NaCoO2.inp", "r") as f:
        topas_example = f.read()

    # Create the agent with tools
    agent = Agent(
        model_name,
        system_prompt=f"""You are an agent responsible for performing Rietveld refinements using
 the topas-academic program. You have access to a tool to write topas .inp files to a run directory,
 and a tool to run the refinement and get the results. You perform Rietveld refinements the way
 human researchers do: looking at an X-ray diffraction pattern, deciding which phases are most likely
to be present based on the pattern, then trying some basic refinements and looking at the results before
iterating to get the fit as good as possible.
You can also analyze and understand images that users share with you. Use this to look at images of Rietveld
refinements and plan your next refinement.
Give a summary of what you've done at the end, telling each refinement you did, explaining any errors you found, 
and explaining why you made changes before the next refinement.

Here is an example of a topas input file for refinement of a sample of NaCoO2: {topas_example}
    """,
        tools=[
            save_topas_inp,
            run_topas_refinement,
            get_optimade_cifs,
            plot_refinement_results,
        ],
        instrument=True,
        retries=5,
    )

    return agent


async def chat_loop():
    """Main chat loop for the terminal application"""
    print("🪶 Guillemot chat framework")
    print("=" * 40)
    print("Type 'quit', 'exit', or 'bye' to end the conversation")
    print("Type 'history' to see recent conversation history")
    print("Type 'clear' to clear conversation history")
    print("🖼️  Include image URLs or local file paths for image analysis")
    print("   Examples: 'Describe this image: https://example.com/image.jpg'")
    print("             'What's in this photo? /path/to/image.png'")
    print("=" * 40)

    agent = create_agent()

    while True:
        try:
            # Get user input
            user_input = input("\n💬 You: ").strip()

            # Handle special commands
            if user_input.lower() in ["quit", "exit", "bye"]:
                print("\n👋 Goodbye!")
                break

            if user_input.lower() == "history":
                print("\n📜 Recent Conversation History:")
                print("-" * 30)
                recent_messages = conversation_history.get_recent_messages(10)
                for msg in recent_messages:
                    role_emoji = "💬" if msg["role"] == "user" else "🤖"
                    content = msg["content"]
                    if msg.get("has_image", False):
                        content += " 🖼️"
                    print(f"{role_emoji} {msg['role']}: {content}")
                continue

            if user_input.lower() == "clear":
                conversation_history.messages.clear()
                print("\n🧹 Conversation history cleared!")
                continue

            if not user_input:
                continue

            # Check for image content
            has_image = False
            message_parts = []

            # Check for image URL
            if is_image_url(user_input):
                text_without_url, image_url = extract_image_url(user_input)
                if text_without_url:
                    message_parts.append(text_without_url)
                else:
                    message_parts.append("Please analyze this image:")
                message_parts.append(ImageUrl(url=image_url))
                has_image = True
                print(f"🖼️  Loading image from URL: {image_url}")

            # Check for local image path
            elif is_local_image_path(user_input):
                text_without_path, image_path = extract_local_image_path(user_input)
                image_content = load_local_image(image_path)

                if image_content:
                    if text_without_path:
                        message_parts.append(text_without_path)
                    else:
                        message_parts.append("Please analyze this image:")
                    message_parts.append(image_content)
                    has_image = True
                    print(f"🖼️  Loaded local image: {image_path}")
                else:
                    print("❌ Failed to load image. Proceeding with text only.")
                    message_parts.append(user_input)

            else:
                # No image, just text
                message_parts.append(user_input)

            # Add user message to history
            conversation_history.add_message("user", user_input, has_image=has_image)

            # Prepare context with conversation history
            history_context = conversation_history.get_formatted_history(5)

            # Create the message to send to the agent
            if has_image:
                # For image messages, send the message parts directly
                agent_message = message_parts
            else:
                # For text-only messages, include conversation history
                full_prompt = f"""
                Recent conversation history:
                {history_context}

                Current user message: {user_input}
                """
                agent_message = full_prompt

            print("\n🤖 Assistant: ", end="", flush=True)

            # Run the agent
            result = await agent.run(agent_message)

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


def launch():
    asyncio.run(main())
