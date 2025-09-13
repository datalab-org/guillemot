<div align="center">

# *guiLLeMot*

<img width="600" alt="image" src="https://github.com/user-attachments/assets/f979aa22-6c39-4986-861b-53e37b486642" />

[*Photo: Bill Dix / Audubon Photo
Award*](https://www.audubon.org/field-guide/bird/black-guillemot)

LLM and AI-assisted explorations into fitting of experimental diffraction data, coming at you from Team [*datalab*](https://github.com/datalab-org) for the [2025 LLM Hackathon for Applications in Materials Science and Chemistry](https://llmhackathon.github.io/).

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

### Functionality

 Given experimental X-ray diffraction data, guillemot will set up and run TOPAS refinements using a natural-language interface. Guillemot uses multimodal image input to inspect refinement outputs, and has tools for retrieving structural information from OPTIMADE providers and outputting refinement plots to images.

### Key Tools

- Local file paths automatically parsed as multimodal input (used by agent to read refinement plots)
- `save_topas_inp` — Create and save a TOPAS .inp refinement input file; returns the path to the generated .inp.
- `run_topas_refinement` — Run a TOPAS refinement using a provided .inp and diffraction data; returns paths to result files and logs.
- `get_optimade_structures` — Query OPTIMADE providers for crystal structures
  and provide them in context to the agent.
- `print_structure` — Produce a concise human-readable summary of a single structure for quick inspection.
- `print_structures` — Summarize multiple structures in a compact tabular/list form with basic metadata (ID, formula, space group, lattice, source).
- `plot_refinement_results` — Plot observed vs calculated pattern and residuals, optionally annotate HKL ticks, save PNG, and return the image filepath and binary content.
- `get_sample` and `get_samples` — Download sample metadata from the configured [*datalab*](https://datalab-org.io) to find uploaded XRD patterns.

## License

This hackathon project is released under the terms of the permissive MIT License - see [LICENSE](LICENSE) file for details.
