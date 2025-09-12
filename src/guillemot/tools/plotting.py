from pathlib import Path
from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from guillemot.utils import load_local_image
from pydantic import BaseModel, field_serializer
from pydantic_ai import BinaryContent

matplotlib.use("Agg")  # Use a non-interactive backend to not crash agent


class PlotResultsOutput(BaseModel):
    output_filepath: str
    output_image: BinaryContent

    @field_serializer("output_image")
    def serialize_binarycontent(self, bc: BinaryContent) -> dict:
        return {
            "data": base64.b64encode(bc.data).decode("ascii"),
            "media_type": bc.media_type,
        }


def plot_refinement_results(
    output_file: str,
    save_path: str,
    hkl_file: Optional[str] = None,
    x_range: list[float] | None = None,
) -> PlotResultsOutput:
    """
    A tool that plots the results of a TOPAS refinement from the refinement output file and generates a PNG image.
    Parameters:
        output_file: Path to the TOPAS refinement output file (e.g., "output.txt").
        save_path: Path to save the generated PNG image (e.g., "refinement_plot.png").
        hkl_file: Optional path to the HKL file containing reflection data for tick marks (e.g., "hkl.txt").
        x_range: Optional tuple specifying the x-axis range to zoom in on (e.g., (20, 50)).
    Returns:
        PlotResultsOutput containing the path to the saved image and the image content.
    """

    # ---- Load total pattern ----
    df = pd.read_csv(output_file, sep="\s+", header=None)
    x, yobs, ycalc = df[0], df[1], df[2]

    # ---- Load hkl file ----
    if hkl_file is not None:
        hkl_df = pd.read_csv(hkl_file, sep="\s+", comment="#", header=None)
        hkl_df.sort_values(by=5, inplace=True)  # sort by two-theta
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
        2, 1, sharex=True, gridspec_kw={"height_ratios": [3, 1]}, figsize=(8, 6)
    )

    # Main pattern
    ax_main.plot(x, yobs, "k.", ms=2, label="Observed")
    ax_main.plot(x, ycalc, "r-", lw=1, label="Calculated")

    if hkl_file is not None:
        # Reflection ticks
        ymin, ymax = ax_main.get_ylim()
        tick_base = ymin + 0.0005 * (ymax - ymin)
        # Determine x-limits for tick plotting
        if x_range is not None:
            x_min, x_max = x_range
        else:
            x_min, x_max = x.min(), x.max()
        # Place hkl labels above the maximum of observed or calculated peak intensity at the tick position
        max_label_y = None
        last_label_x = None
        min_label_dx = 0.02 * (x_max - x_min)
        for tt, inten, h_val, k_val, l_val in zip(two_theta, intensity, h, k, l):
            if x_min <= tt <= x_max:
                ax_main.vlines(
                    tt,
                    tick_base,
                    tick_base + inten * 0.1 * (ymax - ymin),
                    color="b",
                    lw=1,
                )
                # If too close to previous label, shift right to prev_x + min_label_dx
                if last_label_x is not None and tt - last_label_x < min_label_dx:
                    # print(last_label_x, tt)
                    label_x = last_label_x + min_label_dx
                else:
                    label_x = tt
                idx = (abs(x - tt)).idxmin()
                y_peak = max(yobs[idx], ycalc[idx])
                label_y = y_peak + 0.05 * (ymax - ymin)
                ax_main.text(
                    label_x,
                    label_y,
                    f"({int(h_val)},{int(k_val)},{int(l_val)})",
                    color="b",
                    fontsize=7,
                    ha="center",
                    va="bottom",
                    rotation=90,
                )
                last_label_x = label_x
                if max_label_y is None or label_y > max_label_y:
                    max_label_y = label_y
        # Add a proxy artist for the legend
        from matplotlib.lines import Line2D

        proxy = Line2D([0], [0], color="b", lw=1, label="hkl ticks")
        handles, labels = ax_main.get_legend_handles_labels()
        handles.append(proxy)
        labels.append("hkl ticks")
        ax_main.legend(handles, labels)

    ax_main.set_ylabel("Intensity")
    # Adjust ylim to provide a buffer for the highest label
    if hkl_file is not None:
        ymin, ymax = ax_main.get_ylim()
        if "max_label_y" in locals() and max_label_y is not None:
            buffer = 0.1 * (ymax - ymin)
            ax_main.set_ylim(ymin, max(max_label_y + buffer, ymax))

    # Residual
    ax_resid.plot(x, yobs - ycalc, "g-", lw=0.7)
    ax_resid.axhline(0, color="gray", ls="--", lw=0.8)
    ax_resid.set_xlabel(r"$2\theta$ (°)")
    ax_resid.set_ylabel("Obs-Calc")

    if x_range is not None:
        ax_resid.set_xlim(x_range[0], x_range[1])
        max_y = max(
            yobs[(x >= x_range[0]) & (x <= x_range[1])].max(),
            ycalc[(x >= x_range[0]) & (x <= x_range[1])].max(),
        )
        ax_main.set_ylim(0, max_y * 1.1)

    plt.tight_layout()
    plt.savefig(save_path, dpi=100, bbox_inches="tight")
    plt.close(fig)  # ensure no GUI resources are kept

    out = PlotResultsOutput(
        output_filepath=save_path, output_image=load_local_image(save_path)
    )

    return out


def load_local_image(image_path: str) -> BinaryContent | None:
    """Load a local image file and return BinaryContent"""
    try:
        path = Path(image_path)
        if not path.exists():
            print(f"❌ Image file not found: {image_path}")
            return None

        if not path.is_file():
            print(f"❌ Path is not a file: {image_path}")
            return None

        # Determine media type based on file extension
        extension = path.suffix.lower()
        media_type_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
        }

        media_type = media_type_map.get(extension, "image/jpeg")

        # Read the image data
        image_data = path.read_bytes()
        return BinaryContent(data=image_data, media_type=media_type)

    except Exception as e:
        print(f"❌ Error loading image: {e}")
        return None


# Example usage:
if __name__ == "__main__":
    plot_refinement_results(
        output_file="examples/FeSb_19RBM/Runs/1/output.txt",
        save_path="test_plot.png",
        hkl_file="examples/FeSb_19RBM/Runs/1/hkl.txt",
        # x_range=(40, 50),
    )
