import os
import subprocess
from os.path import join
from typing import Optional
import matplotlib.pyplot as plt
import pandas as pd

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

    outfile_path = inp_path.replace(".inp", ".out")
    with open(outfile_path) as f:
        outfile_contents = f.read()

    refinement_result_path = inp_path.replace(".inp", "_output.txt")

    def plot_refinement_results(refinement_result_path: str):
        df = pd.read_csv(refinement_result_path, delim_whitespace=True, comment="#")
        plt.figure()
        plt.plot(df["2Theta"], df["Yobs"], "o", label="Observed")
        plt.plot(df["2Theta"], df["Ycalc"], "-", label="Calculated")
        plt.plot(df["2Theta"], df["Yobs"] - df["Ycalc"], "-", label="Difference")
        plt.xlabel("2Theta")
        plt.ylabel("Intensity")
        plt.legend()
        plt.title("Topas Refinement Results")

    # todo: add tail of log file located at \Science\Topas-7\topas.log
    # todo: make graph of result

    return RunRefinementResult(
        status=status,
        outfile_path=outfile_path,
        outfile_contents=outfile_contents,
        refinement_result_path=refinement_result_path,
        stdout=result.stdout,
        stderr=result.stderr,
    )
