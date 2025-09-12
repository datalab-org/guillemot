from datalab_api import DatalabClient
import os
from pathlib import Path
from pydantic_ai import ModelRetry


def get_samples():
    """Get a list of all samples available in the Datalab
    and list whether they have XRD data."""
    client = DatalabClient("demo.datalab-org.io")
    samples = client.get_items("samples")
    return samples


def get_sample(sample_id: str | None):
    """Get a sample with the given ID and download its associated data files."""
    client = DatalabClient("demo.datalab-org.io")
    sample = client.get_item(sample_id)
    orig_dir = Path(os.getcwd()).absolute()
    try:
        os.makedirs(f"./data/{sample_id}", exist_ok=True)
        os.chdir(f"./data/{sample_id}")
        files = client.get_item_files(sample_id)
        return sample, files

    finally:
        os.chdir(str(orig_dir))


def list_data_files(sample_id: str):
    """List data files that have been downloaded for a given sample."""
    return os.listdir(f"./data/{sample_id}")
