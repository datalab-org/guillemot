import matplotlib.pyplot as plt
import pandas as pd
from typing import Optional

def plot_refinement_results(output_file: str, save_path: str, hkl_file: Optional[str]=None):
    # ---- Load total pattern ----
    df = pd.read_csv(output_file, sep="\s+", header=None)
    x, yobs, ycalc = df[0], df[1], df[2]

    # ---- Load hkl file ----
    if hkl_file is not None:
        hkl_df = pd.read_csv(hkl_file, delim_whitespace=True, comment="#", header=None)
        h = hkl_df[0]
        k = hkl_df[1]
        l = hkl_df[2]
        M = hkl_df[3]
        d_spacing = hkl_df[4]
        two_theta = hkl_df[5]
        intensity = hkl_df[6]

        # ---- Normalize tick intensities ----
        intensity /= intensity.max()  # scale to [0,1]

    # ---- Plot ----
    fig, (ax_main, ax_resid) = plt.subplots(
        2, 1, sharex=True, gridspec_kw={"height_ratios": [3,1]}, figsize=(8,6)
    )

    # Main pattern
    ax_main.plot(x, yobs, "k.", ms=2, label="Observed")
    ax_main.plot(x, ycalc, "r-", lw=1, label="Calculated")

    if hkl_file is not None:
        # Reflection ticks
        ymin, ymax = ax_main.get_ylim()
        tick_base = ymin + 0.0005*(ymax - ymin)
        for tt, inten in zip(two_theta, intensity):
            ax_main.vlines(tt, tick_base, tick_base + inten*0.1*(ymax-ymin), color="b", lw=1)

    ax_main.set_ylabel("Intensity")
    ax_main.legend()

    # Residual
    ax_resid.plot(x, yobs - ycalc, "g-", lw=0.7)
    ax_resid.axhline(0, color="gray", ls="--", lw=0.8)
    ax_resid.set_xlabel(r"$2\theta$ (°)")
    ax_resid.set_ylabel("Obs-Calc")

    plt.tight_layout()
    
    plt.savefig(save_path)

# Example usage:
plot_refinement_results(
    output_file="examples/FeSb_19RBM/Runs/1/output.txt", 
    save_path="examples/FeSb_19RBM/Runs/1/plot",
    hkl_file="examples/FeSb_19RBM/Runs/1/hkl.txt"
)
