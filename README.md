<div align="center">

# *guiLLeMot*

<img width="600" alt="image" src="https://github.com/user-attachments/assets/f979aa22-6c39-4986-861b-53e37b486642" />

LLM and AI-assisted explorations into fitting of experimental diffraction data, coming at you from Team [*datalab*](https://github.com/datalab-org) for the 2025 LLM hackathon.

</div>

## Setup

1. Ensure you have [`uv`](https://astral.sh/uv) installed
2. Install dependencies:
   ```bash
   uv sync --all-extras --dev
   ```

3. Set up your environment variables in `.env`:
   ```bash
   AI_MODEL=google-gla:gemini-2.5-flash-lite
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

Run the chat application:
```bash
uv run guillemot
```

### Available Commands

- **Chat normally**: Just type your message and press Enter
- **Image analysis**: Include image URLs or local file paths in your message
  - `"Describe this image: https://example.com/photo.jpg"`
  - `"What's in this picture? /path/to/local/image.png"`
- **`history`**: View recent conversation history (🖼️ indicates messages with images)
- **`clear`**: Clear conversation history
- **`quit`**, **`exit`**, or **`bye`**: Exit the application

### Tool Usage

- `save_topas_inp` — Create and save a TOPAS .inp refinement input file; returns the path to the generated .inp.
- `run_topas_refinement` — Run a TOPAS refinement using a provided .inp and diffraction data; returns paths to result files and logs.
- `get_optimade_cifs` — Query OPTIMADE providers for crystal structures and save CIFs locally; returns downloaded file paths and basic metadata.

### Image Analysis

The app parses image input from URLs or local files. Usage examples:

**Analyze images from URLs:**
```
Describe this logo: https://example.com/logo.png
What colors are in this image? https://example.com/photo.jpg
```

**Analyze local image files:**
```
What's in this photo? /Users/username/Pictures/vacation.jpg
Analyze this screenshot: ./screenshot.png
```

**Supported formats:** JPG, JPEG, PNG, GIF, BMP, WebP

The AI can describe images, identify objects, read text in images, analyze colors, and answer questions about image content.

## Architecture

### Core Components

- **ConversationHistory**: Manages chat memory and context with image tracking
- **Agent**: pydantic-ai agent with tool support and multimodal capabilities
- **Image Processing**: URL and local file image loading with multiple format support
- **Interactive Loop**: Clean terminal-based chat experience

### Memory System

The conversation history is maintained in memory and provides context to the AI:
- Stores user and assistant messages with timestamps
- Formats recent messages for AI context
- Configurable history limits

## Extending the Application

### Adding New Tools

1. Create a new tool in a python file in `src/guillemot/tools/`

2. Add it to the agent:
   ```python

   agent = Agent(
       # ...
       tools=[tool_1, tool_2],
       # ...
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
