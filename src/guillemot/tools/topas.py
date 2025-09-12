import os
import pathlib
import subprocess
from os.path import join
from typing import Optional

from guillemot.tools.plotting import PlotResultsOutput, plot_refinement_results
from pydantic import BaseModel
from pydantic_ai.exceptions import ModelRetry

RUN_DIR = "run_dir"


class SaveInpResult(BaseModel):
    inp_path: str
    line_count: int


def save_topas_inp(filename: str, inp_text: str) -> SaveInpResult:
    """
    A tool that writes a topas .inp file to ./run_dir/ and does some basic checks.
    The AI model must make sure that the .inp file includes the export lines:
    Out_X_Yobs_Ycalc("<filename>_output.txt")

    Each str block should also have:
    Out_CIF_STR("<filename>_<phase_name>.cif"). Note that the input filename (without ".inp")

    should prefix the phase name.

    Blocks are only defined by whitespace and do not need closing tags.

    The input pattern can be assumed to be in the same directory that TOPAS runs from and in the same dir as input file is.
    """
    basename = os.path.splitext(filename)[0]

    os.makedirs(RUN_DIR, exist_ok=True)
    inp_path = join(RUN_DIR, f"{basename}.inp")

    # Build the expected macro string, then check presence
    output_macro_text = f'Out_X_Yobs_Ycalc("{basename}_output.txt")'
    if output_macro_text not in inp_text:
        raise ModelRetry(
            message=f"input file doesn't contain the correct output macro: {output_macro_text}. Please try again."
        )

    with open(inp_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(inp_text)
    lines = inp_text.splitlines()

    return SaveInpResult(
        inp_path=inp_path,
        line_count=len(lines),
    )


class RunRefinementResult(BaseModel):
    status: str  # "success" | "failure" | "timeout"
    stdout: str
    stderr: str
    outfile_path: Optional[str]
    outfile_contents: Optional[str]
    refinement_result_path: Optional[str]
    logs_tail: Optional[str]
    plot_results: Optional[PlotResultsOutput]
    # aux_files: list[str] = Field(default_factory=list)  # any xy/csv exports found


def run_topas_refinement(inp_path: str, timeout_s: int = 60) -> RunRefinementResult:
    try:
        result = subprocess.run(
            [r"\Science\Topas-7\tc.exe", inp_path],
            timeout=timeout_s,
            text=True,
            capture_output=True,
        )
        status = "success" if result.returncode == 0 else "failure"
    except subprocess.TimeoutExpired:
        status = "timeout"

    if status == "failure":
        raise ModelRetry(
            f"TOPAS perhaps returned an error. stdout: {result.stdout}, {result.stderr}"
        )

    outfile_path = pathlib.Path(inp_path.replace(".inp", ".out"))
    outfile_path = str(outfile_path)

    if os.path.isfile(outfile_path):
        with open(outfile_path) as f:
            outfile_contents = f.read()
    else:
        outfile_contents = None
        outfile_path = None

    refinement_result_path = inp_path.replace(".inp", "_output.txt")
    # Check if the refinement result file exists
    if not os.path.isfile(refinement_result_path):
        refinement_result_path = None

    hkl_file = inp_path.replace(".inp", "_hkl.txt")
    if not os.path.isfile(hkl_file):
        hkl_file = None

    # Only plot if the result file exists
    plot_results = None
    if refinement_result_path is not None:
        save_path = refinement_result_path.replace("_output.txt", "_plot.png")
        plot_results = plot_refinement_results(
            output_file=refinement_result_path, save_path=save_path, hkl_file=hkl_file
        )

    # todo: add tail of log file located at \Science\Topas-7\topas.log
    # todo: make graph of result

    return RunRefinementResult(
        status=status,
        outfile_path=outfile_path,
        outfile_contents=outfile_contents,
        refinement_result_path=refinement_result_path,
        stdout=result.stdout,
        stderr=result.stderr,
        logs_tail=None,
        plot_results=plot_results,
    )
