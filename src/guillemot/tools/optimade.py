from typing import Literal
from optimade.client import OptimadeClient
from optimade.adapters import Structure
from pathlib import Path
import re
from pydantic_ai import ModelRetry

from rich.table import Table
from rich.console import Console


def _create_optimade_elements_filter(elements: list[str]) -> str:
    """Creates an OPTIMADE filter string for an exclusive list of elements."""

    quoted_elements = [f'"{el}"' for el in elements]

    if len(elements) > 1:
        _filter = f"elements HAS ALL {','.join(quoted_elements)} AND elements LENGTH {len(quoted_elements)}"
    else:
        _filter = f"elements HAS {quoted_elements[0]} AND elements LENGTH 1"

    return _filter


def _sanitize_formula(formula: str) -> str:
    elements = tuple(re.findall(r"[A-Z][a-z]?", formula))
    numbers = re.split(r"[A-Z][a-z]?", formula)[1:]
    numbers = [str(int(num)) if num and str(num) != "1" else "" for num in numbers]

    # sort elements alphabetically and reassemble formula
    sorted_formula = "".join(f"{el}{num}" for el, num in sorted(zip(elements, numbers)))
    return sorted_formula


def get_optimade_cifs(
    elements: list[str] | None = None,
    formula: str | None = None,
    query: str | None = None,
    database: Literal["cod", "mp"] = "cod",
) -> list[dict]:
    """
    Perform an OPITIMADE query for a set of elements or a formula to a restricted set of databases
    and save all cif files in the `./cifs` directory, named by database ID and entry ID, e.g.,
    `mp-1234.cif` or `cod-1234567.cif`.

    Parameters:
        elements: A list of element symbols to query for, e.g., ["Li", "C", "O"].
            Will be treated as an OPTIMADE `HAS ONLY` query, i.e., ?filter=elements HAS ONLY "Li", "C", "O",
            or equivalently ?filter=elements HAS ALL "Li", "C", "O" AND elements LENGTH 3.
        formula: A chemical formula to query for, e.g., "LiFePO4". If provided, this takes precedence over `elements`, will
            be sanitized (elements sorted alphabetically, e.g., "FeLiO4P"), and an exact match will be performed.
        query: A raw OPTIMADE query, that will take precedence. These can be more expressive and used to e.g., search for a different
            number of elements, or to add additional constraints.
        database: The database to query, one of "cod" (Crystallography Open Database),
            "mp" (Materials Project), or "oqmd" (Open Quantum Materials Database).

    Returns:
        A list of optimade Structure objects.

    """

    allowed_database_endpoints = {
        "cod": "https://www.crystallography.net/cod/optimade/",
        "mp": "https://optimade.materialsproject.org",
        "oqmd": "https://oqmd.org/optimade",
    }

    if database not in allowed_database_endpoints:
        raise RuntimeError(
            f"Unknown database {database!r}. Must be one of 'cod', 'mp', or 'oqmd'."
        )

    endpoint = allowed_database_endpoints[database]
    client = OptimadeClient(endpoint)

    if query:
        _filter = query

    elif elements:
        if not isinstance(elements, list):
            raise RuntimeError(
                f"`elements` must be a list of element symbols, not {type(elements)}."
            )

        _filter = _create_optimade_elements_filter(elements)

    elif formula:
        if database == "cod":
            raise ModelRetry("Use elements rather than formula for cod search")
        formula = _sanitize_formula(formula)
        _filter = f'chemical_formula_reduced="{formula}"'

    else:
        raise RuntimeError("Must provide either `elements` or `formula` or `query`.")

    # response fields required to make a CIF
    response_fields = [
        "elements",
        "structure_features",
        "nsites",
        "species_at_sites",
        "species",
        "cartesian_site_positions",
        "last_modified",
        "lattice_vectors",
        "nperiodic_dimensions",
        "dimension_types",
    ]

    results = client.get(
        _filter,
        response_fields=response_fields,
    )

    raw_structures = results["structures"][_filter][endpoint]["data"]

    if not raw_structures:
        raise RuntimeError(
            f"No structures found for {elements=}, {formula=} in {database=}."
        )

    print(
        f"Found {len(raw_structures)} structures with {elements=}, {formula=} in {database=}"
    )

    return [Structure(d).as_dict for d in raw_structures]

def print_structures(structures: list[dict]) -> str:
    """Prints the structure query results.

    Parameters:
        structures: A list of optimade Structure objects.

    """
    table = Table(title="OPTIMADE Structures")
    console = Console()

    table.add_column("#")
    table.add_column("Formula")
    table.add_column("Spacegroup")
    table.add_column("a (Å)", justify="right")
    table.add_column("b (Å)", justify="right")
    table.add_column("c (Å)", justify="right")
    table.add_column("α (°)", justify="right")
    table.add_column("β (°)", justify="right")
    table.add_column("γ (°)", justify="right")
    table.add_column("Disordered?")

    for ind, s in enumerate(structures):

        s = Structure(s).as_pmg


        try:
            spacegroup = s.get_symmetry_dataset()["international"]
        except Exception:
            spacegroup = None

        table.add_row(
            structures[ind]["id"],
            s.reduced_formula.translate(str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")),
            spacegroup,
            f"{s.lattice.a:.1f}",
            f"{s.lattice.b:.1f}",
            f"{s.lattice.c:.1f}",
            f"{s.lattice.alpha:.0f}",
            f"{s.lattice.beta:.0f}",
            f"{s.lattice.gamma:.0f}",
            "Yes" if "disorder" in structures[ind]["attributes"]["structure_features"] else "No",
        )

    console.print(table)

    return str(table)

def print_structure(structure: dict) -> str:
    """Focus in on a single structure and print the lattice, atom positions and space group to
    be used when creating a topas input.

    Paramters:
        structure: An optimade Structure object.

    """
    pmg = Structure(structure).as_pmg
    print(pmg)
    return str(pmg)

