# Guillemot LLM Chat App

A terminal-based LLM application using pydantic-ai with conversation memory and tool support.

## Features

- 🤖 **AI-powered chat**: Uses Gemini 2.5 Flash Lite model via pydantic-ai
- 🧠 **Memory**: Maintains conversation history across interactions
- 🔧 **Tool support**: Includes a dummy tool that can be extended with real functionality
- 💬 **Interactive terminal interface**: Clean, emoji-enhanced chat experience
- ⚙️ **Environment-based configuration**: API keys and model settings via .env file

## Setup

1. Ensure you have Python 3.10+ installed
2. Install dependencies:
   ```bash
   uv sync
   ```

3. Set up your environment variables in `.env`:
   ```bash
   AI_MODEL=google-gla:gemini-2.5-flash-lite
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

Run the chat application:
```bash
python main.py
```

### Available Commands

- **Chat normally**: Just type your message and press Enter
- **`history`**: View recent conversation history
- **`clear`**: Clear conversation history
- **`quit`**, **`exit`**, or **`bye`**: Exit the application

### Tool Usage

The app includes a dummy tool that the AI can call when appropriate. Try asking questions like:
- "Can you use a tool to get some data?"
- "Please call the dummy tool with 'test query'"

## Architecture

### Core Components

- **ConversationHistory**: Manages chat memory and context
- **DummyToolResult**: Pydantic model for tool responses
- **Agent**: pydantic-ai agent with tool support
- **Chat Loop**: Interactive terminal interface

### Tool System

The dummy tool demonstrates how to integrate external functionality:

```python
def dummy_tool(query: str) -> DummyToolResult:
    """Example tool that returns structured data"""
    return DummyToolResult(
        result="This is a dummy response! The tool is working correctly.",
        timestamp=datetime.now().isoformat(),
        input_received=query
    )
```

To add real tools, replace or extend this function with actual API calls, database queries, or other external services.

### Memory System

The conversation history is maintained in memory and provides context to the AI:
- Stores user and assistant messages with timestamps
- Formats recent messages for AI context
- Configurable history limits

## Extending the Application

### Adding New Tools

1. Create a new tool function:
   ```python
   def weather_tool(location: str) -> WeatherResult:
       # Your tool implementation
       pass
   ```

2. Add it to the agent:
   ```python
   agent = Agent(
       model_name,
       tools=[dummy_tool, weather_tool],
       # ... other config
   )
   ```

### Customizing the AI Behavior

Modify the `system_prompt` in the `create_agent()` function to change how the AI behaves.

### Persisting Conversation History

Currently, history is stored in memory. To persist across sessions, modify the `ConversationHistory` class to save/load from a file or database.

## Dependencies

- `pydantic-ai`: LLM framework with structured outputs and tool support
- `python-dotenv`: Environment variable management
- `logfire`: Logging and observability (optional)

## License

MIT License - see LICENSE file for details.
