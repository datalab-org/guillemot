from typing import Literal
from optimade.client import OptimadeClient
from optimade.adapters import Structure
from pathlib import Path
import re
from urllib.request import urlopen
from pydantic_ai import ModelRetry
from pymatgen.io.cif import CifWriter

from guillemot.vendor.topas_inp_writer.cif_to_str import convert as cif_to_str
from rich.table import Table
from rich.console import Console


COD_CIF_BASE = "https://www.crystallography.net/cod"


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


def _cod_cif_url(structure: dict) -> str | None:
    self_url = str((structure.get("links") or {}).get("self", ""))
    if "crystallography.net/cod/optimade/" not in self_url:
        return None
    return f"{COD_CIF_BASE}/{structure['id']}.cif"


def _cif_topas_str(path: Path, source: str, use_adps: bool) -> str:
    text, warnings = cif_to_str(path, use_adps=use_adps)
    output = f"' {source}\n' Saved CIF: {path.resolve()}\n{text}"
    if warnings:
        output += "\n\n' Conversion warnings:\n" + "\n".join(
            f"' - {warning}" for warning in warnings
        )
    return output


def _cod_topas_str(structure: dict, use_adps: bool = False) -> str | None:
    url = _cod_cif_url(structure)
    if url is None:
        return None

    try:
        with urlopen(url, timeout=30) as response:
            cif_bytes = response.read()
    except OSError as exc:
        raise ModelRetry(f"Could not download {url}: {exc}") from exc

    path = Path(f"{structure['id']}.cif")
    path.write_bytes(cif_bytes)
    return _cif_topas_str(path, f"Source CIF: {url}", use_adps)


def _mp_topas_str(structure: dict, use_adps: bool = False) -> str | None:
    structure_id = str(structure.get("id", ""))
    if not structure_id.startswith("mp-"):
        return None

    path = Path(f"{structure_id}.cif")
    pmg = Structure(structure).as_pymatgen
    CifWriter(pmg, symprec=0.01, angle_tolerance=5, refine_struct=True).write_file(path)
    source = (
        f"Source structure: https://materialsproject.org/materials/{structure_id}\n"
        "' Symmetry inferred by pymatgen/spglib (symprec 0.01 A, angle tolerance 5 degrees)"
    )
    return _cif_topas_str(path, source, use_adps)


def get_optimade_structures(
    elements: list[str] | None = None,
    formula: str | None = None,
    query: str | None = None,
    database: Literal["cod", "mp"] = "cod",
) -> list[dict]:
    """
    Perform an OPITIMADE query for a set of elements or a formula to a restricted set of databases.
    Results will be returned as a list which can be printed or processed further.

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
        A list of optimade structures as dicts to be printed using the `print_structures` tool.

    """

    allowed_database_endpoints = {
        "cod": "https://www.crystallography.net/cod/optimade/",
        "mp": "https://optimade.materialsproject.org",
        "oqmd": "https://oqmd.org/optimade",
    }

    if database not in allowed_database_endpoints:
        raise ModelRetry(
            f"Unknown database {database!r}. Must be one of 'cod', 'mp', or 'oqmd'."
        )

    endpoint = allowed_database_endpoints[database]
    client = OptimadeClient(endpoint)

    if query:
        _filter = query

    elif elements:
        if not isinstance(elements, list):
            raise ModelRetry(
                f"`elements` must be a list of element symbols, not {type(elements)}."
            )

        _filter = _create_optimade_elements_filter(elements)

    elif formula:
        if database == "cod":
            raise ModelRetry("Use elements rather than formula for cod search")
        formula = _sanitize_formula(formula)
        _filter = f'chemical_formula_reduced="{formula}"'

    else:
        raise ModelRetry("Must provide either `elements` or `formula` or `query`.")

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
        raise ModelRetry(
            f"No structures found for {elements=}, {formula=} in {database=}."
        )

    print(
        f"Found {len(raw_structures)} structures with {elements=}, {formula=} in {database=}"
    )

    return [Structure(d).as_dict for d in raw_structures]


def print_structures(structures: list[dict]) -> str:
    """Prints the structure query results.

    MUST use all the fields provided by OPTIMADE.

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
        s = Structure(s).as_pymatgen

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
            "Yes"
            if "disorder" in structures[ind]["attributes"]["structure_features"]
            else "No",
        )

    console.print(table)

    return str(table)


def print_structure(structure: dict, use_adps: bool = False) -> str:
    """Focus in on a single structure and print the lattice, atom positions and space group to
    be used when creating a topas input.

    MUST use all the fields provided by OPTIMADE.

    Paramters:
        structure: An optimade Structure object.
        use_adps: Emit anisotropic displacement parameters when available.

    """
    for converter in (_cod_topas_str, _mp_topas_str):
        topas_str = converter(structure, use_adps=use_adps)
        if topas_str is not None:
            print(topas_str)
            return topas_str

    pmg = Structure(structure).as_pymatgen
    print(pmg)
    return str(pmg)
