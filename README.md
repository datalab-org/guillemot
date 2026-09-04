<div align="center">

# *guiLLeMot*

<img width="600" alt="image" src="https://github.com/user-attachments/assets/f979aa22-6c39-4986-861b-53e37b486642" />

[*Photo: Bill Dix / Audubon Photo
Award*](https://www.audubon.org/field-guide/bird/black-guillemot)

LLM and AI-assisted explorations into fitting of experimental diffraction data, coming at you from Team [*datalab*](https://github.com/datalab-org) for the [2025 LLM Hackathon for Applications in Materials Science and Chemistry](https://llmhackathon.github.io/).

</div>

## Setup

1. Install [`uv`](https://astral.sh/uv), then the dependencies:

   ```bash
   uv sync --all-extras --dev
   ```

2. Create a `.env` file with a model and its API key:

   ```bash
   GUILLEMOT_AI_MODEL=google-gla:gemini-2.5-flash-lite
   GEMINI_API_KEY=your_api_key_here
   ```

3. Tell it where TOPAS lives — see [Running TOPAS over SSH](#running-topas-over-ssh).

## End-to-end example

One refinement, start to finish, without a conversation:

```bash
uv run guillemot --pattern examples/KD1-2_5_NaCoO2/KD1-2_5-90_30min.xy --elements Na,Co,O
```

```
🪶 Guillemot
📁 Session directory: run_dir/20260816-182534-4153a2
📈 Pattern: examples/KD1-2_5_NaCoO2/KD1-2_5-90_30min.xy
🧪 Elements: Na, Co, O
============================================================
Found 13 structures with elements=['Na', 'Co', 'O'] in database='cod'
Full Formula (Na1.56 Co2 O4) ...
▶ running TOPAS on topas-vm1 in C:\Users\Group_User\guillemot\KD1-2_5_NaCoO2_20260816_182553
TOPAS-64 Version 6 (c) 1992-2016 Alan A. Coelho
   ...
File KD1-2_5_NaCoO2_output.txt written to.
```

Afterwards everything from that run is in one directory:

```
run_dir/20260816-182534-4153a2/
├── KD1-2_5-90_30min.xy              # the pattern, copied in
├── KD1-2_5_NaCoO2.inp               # what the agent wrote
└── KD1-2_5_NaCoO2_20260816_182553/  # synced back from the TOPAS machine
    ├── KD1-2_5_NaCoO2.out
    ├── KD1-2_5_NaCoO2_output.txt
    ├── KD1-2_5_NaCoO2_plot.png
    └── KD1-2_5_NaCoO2_riet_01.cif
```

`--elements` is how you say what you think is in the sample. Leave it out and the agent will
try to read the composition off the filename, and tell you if it can't rather than guessing.
`--notes` passes anything else along ("measured on a Co source", "should be single phase").

Run the chat application:
```bash
uv run guillemot
```

## Running TOPAS over SSH

TOPAS usually lives on a separate Windows machine. Point guillemot at it in `.env`:

```bash
GUILLEMOT_TOPAS_SSH_HOST=user@topas-pc              # or a ~/.ssh/config host alias
GUILLEMOT_TOPAS_EXE='C:\Science\Topas-7\tc.exe'     # remote path to the TOPAS console exe
GUILLEMOT_TOPAS_REMOTE_DIR='C:\guillemot_runs'      # remote directory for run directories
GUILLEMOT_TOPAS_SSH_PORT=22                         # optional, only if non-standard
```

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

## System prompts

The system prompts live in `src/guillemot/prompts/` as one markdown file per variant, so
wordings can be compared without touching the application. Pick one with `--prompt`, or set
`GUILLEMOT_PROMPT`; `guillemot --list-prompts` shows what is there.

```shell
guillemot --list-prompts
guillemot --prompt concise --pattern examples/HL2-1/HL2-1_2.xy
guillemot --prompt ~/experiments/terse-with-hkl.md    # a path works too
```

A prompt is filled in before it is sent: `{{execution}}` becomes the instructions for wherever
TOPAS is actually running (local, or over SSH — the fragments in `prompts/fragments/`), and
`{{topas_example}}` becomes the worked NaCoO2 example. Both must appear in any new variant;
leaving one out is an error at start-up rather than a placeholder sent to the model.

## Tracing

Each run is instrumented with [Logfire](https://logfire.pydantic.dev).
Each session has its log written to `trace.jsonl` in that session's directory, one JSON object per line, so the record of
what the agent did sits alongside the .inp files and plots it produced.
Setting `LOGFIRE_TOKEN` additionally sends the same spans to the Logfire dashboard for nicer visualisation.

## License

This hackathon project is released under the terms of the permissive MIT License - see [LICENSE](LICENSE) file for details.
