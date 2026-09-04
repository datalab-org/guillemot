import argparse
import asyncio
import os

from dotenv import load_dotenv
from guillemot.tools import (
    check_remote_topas_running,
    get_optimade_structures,
    list_available_data,
    print_structure,
    print_structures,
    plot_refinement_results,
    run_topas_refinement,
    run_topas_refinement_remote,
    save_topas_inp,
)
from guillemot.model import build_model, build_model_settings, context_limit
from guillemot.prompts import (
    available_prompts,
    fill,
    load_fragment,
    render_prompt,
    selected_prompt_name,
)
from guillemot.session import copy_into_session, current_session, start_session
from guillemot.streaming import run_and_show
from guillemot.tracing import configure_tracing
from guillemot.tools.datalab import get_sample, get_samples, list_data_files
from pydantic_ai import Agent
from guillemot.utils import (
    ConversationHistory,
    extract_local_image_path,
    is_local_image_path,
    load_local_image,
)

# Load environment variables
load_dotenv()


# Initialize conversation history
conversation_history = ConversationHistory(messages=[])

# How much context the configured model can hold, filled in once the model is known.
# None when we have no trustworthy number, in which case the meter shows tokens only.
CONTEXT_LIMIT: int | None = None


# Set up the pydantic-ai agent
def create_agent(prompt: str | None = None) -> Agent:
    """Create and configure the pydantic-ai agent.

    `prompt` names the system prompt to run with — one of the variants in
    `guillemot.prompts`, or a path to a markdown file of your own. Defaults to
    whatever `GUILLEMOT_PROMPT` says, and to `default` otherwise.
    """

    # Get model and API key from environment. `build_model` adds retries for rate
    # limiting (HTTP 429), which would otherwise abort the run mid-refinement.
    model_name = os.getenv("GUILLEMOT_AI_MODEL", "gemini-2.5-flash-lite")
    model = build_model(model_name)
    # Without this the model's reasoning never reaches us, and there is nothing for the
    # chat loop to show while it works.
    model_settings = build_model_settings(model_name)

    global CONTEXT_LIMIT
    CONTEXT_LIMIT = context_limit(model_name)

    # One working directory per conversation, so this refinement's files stay together
    # and cannot be mixed up with an earlier one's. The trace of the run is written
    # there too, so what the agent did is kept with what it produced.
    session = start_session()
    configure_tracing()

    with open("examples/NaCoO2/example_refinement_NaCoO2.inp", "r") as f:
        topas_example = f.read()

    # Where TOPAS actually runs decides which tool the model should reach for, so that
    # part of the prompt is chosen here rather than written into every variant.
    remote_host = os.getenv("GUILLEMOT_TOPAS_SSH_HOST")
    if remote_host:
        execution = fill(load_fragment("execution_remote"), remote_host=remote_host)
    else:
        execution = load_fragment("execution_local")

    prompt_name = prompt or selected_prompt_name()
    system_prompt = render_prompt(
        prompt_name, execution=execution, topas_example=topas_example
    )
    print(f"📝 System prompt: {prompt_name}")

    # Create the agent with tools
    agent = Agent(
        model,
        system_prompt=system_prompt,
        tools=[
            list_available_data,
            copy_into_session,
            save_topas_inp,
            # run_topas_refinement,
            run_topas_refinement_remote,
            check_remote_topas_running,
            get_optimade_structures,
            print_structure,
            print_structures,
            plot_refinement_results,
            get_samples,
            get_sample,
            list_data_files,
        ],
        model_settings=model_settings,
        instrument=True,
        retries=5,
    )

    return agent


async def chat_loop(prompt: str | None = None):
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

    agent = create_agent(prompt)
    session = current_session()
    if session is not None:
        print(f"📁 Session directory: {session.directory}")

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

            # Check for local image path
            if is_local_image_path(user_input):
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

            # Run the agent, showing its reasoning while it works
            response_text = await run_and_show(agent, agent_message, CONTEXT_LIMIT)

            print("🤖 Assistant: ", end="", flush=True)
            print(response_text)

            # Add assistant response to history
            conversation_history.add_message("assistant", response_text)

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again or type 'quit' to exit.")


def build_task(
    pattern: str = None,
    elements: list[str] | None = None,
    opxrd_pattern: int | None = None,
    notes: str | None = None,
) -> str:
    """Write the instruction for a one-shot refinement started from the command line."""
    task = [
        f"Refine the diffraction pattern in the file `{pattern}`.",
        "Work through it end to end without asking me anything: copy the pattern into "
        "the session directory, write a TOPAS input file for it, run the refinement, "
        "and then tell me the Rwp and what you would try next.",
    ]
    if elements:
        task.insert(1, f"The sample is believed to contain: {', '.join(elements)}.")
    else:
        task.insert(
            1,
            "I have not told you the composition, so work out what you can from the "
            "filename; if you genuinely cannot, say so instead of guessing.",
        )
    if notes:
        task.append(f"Additional context from me: {notes}")
    return "\n".join(task)


async def run_once(
    pattern: str,
    elements: list[str] | None = None,
    notes: str | None = None,
    opxrd_pattern: int | None = None,
    prompt: str | None = None,
) -> str:
    """Run a single refinement from the command line and print the result."""
    agent = create_agent(prompt)
    session = current_session()

    print("🪶 Guillemot")
    print(f"📁 Session directory: {session.directory if session else 'run_dir'}")
    print(f"📈 Pattern: {pattern}")
    print(f"🧪 Elements: {', '.join(elements) if elements else 'not given'}")
    print("=" * 60)

    output = await run_and_show(
        agent, build_task(pattern, opxrd_pattern, elements, notes), CONTEXT_LIMIT
    )
    print(output)
    print("=" * 60)
    if session is not None:
        print(f"📁 Everything from this run is in {session.directory}")
    return output


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="guillemot",
        description=(
            "Run TOPAS Rietveld refinements with an LLM agent. With no arguments, "
            "starts an interactive chat; give --pattern to run one refinement and exit."
        ),
    )
    parser.add_argument(
        "--pattern",
        help="path to the diffraction pattern to refine, e.g. examples/HL2-1/HL2-1_2.xy",
    )
    parser.add_argument(
        "--opxrd-pattern",
        help="Load a pattern from a local copy of the opXRD database.",
    )
    parser.add_argument(
        "--elements",
        help="comma-separated elements believed to be present, e.g. Ag,Cu,Pd",
    )
    parser.add_argument(
        "--notes", help="anything else the agent should know about the sample"
    )
    parser.add_argument(
        "--prompt",
        help=(
            "which system prompt to run with: one of "
            f"{', '.join(available_prompts())}, or the path to a markdown file. "
            "Overrides GUILLEMOT_PROMPT."
        ),
    )
    parser.add_argument(
        "--list-prompts",
        action="store_true",
        help="show the available system prompts and exit",
    )
    return parser.parse_args(argv)


async def main(args: argparse.Namespace) -> None:
    """Main entry point"""
    try:
        if args.list_prompts:
            print("Available system prompts:")
            for name in available_prompts():
                marker = " (default)" if name == selected_prompt_name() else ""
                print(f"  {name}{marker}")
            return

        if args.pattern:
            elements = (
                [e.strip() for e in args.elements.split(",") if e.strip()]
                if args.elements
                else None
            )
            await run_once(
                args.pattern, elements, args.opxrd_pattern, args.notes, args.prompt
            )
        else:
            await chat_loop(args.prompt)
    except Exception as e:
        print(f"❌ Failed to run guillemot: {e}")
        print("Check your .env file: GUILLEMOT_AI_MODEL and the matching API key.")


def launch():
    asyncio.run(main(parse_args()))
