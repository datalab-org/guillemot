from typing import Literal
from optimade.client import OptimadeClient
from optimade.adapters import Structure
from pathlib import Path
import re
import tempfile
from urllib.parse import urlencode
from urllib.request import urlopen
from pydantic_ai import ModelRetry

from guillemot.vendor.topas_inp_writer.cif_to_str import convert as cif_to_str
from rich.table import Table
from rich.console import Console


COD_OPTIMADE_VERSION = "v1.3.0"
COD_CIF_BASE = "https://www.crystallography.net/cod"
SYMMETRY_RESPONSE_FIELDS = [
    "space_group_it_number",
    "space_group_symbol_hall",
    "space_group_symbol_hermann_mauguin",
    "space_group_symbol_hermann_mauguin_extended",
    "space_group_symmetry_operations_xyz",
]


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


def _without_symmetry_fields(structure: dict) -> dict:
    """Copy a record without fields that some providers format nonconformingly."""

    stripped = {**structure, "attributes": structure["attributes"].copy()}
    for field in SYMMETRY_RESPONSE_FIELDS:
        stripped["attributes"].pop(field, None)
    return stripped


def _adapt_structure(structure: dict) -> dict:
    """Adapt geometry while retaining deposited symmetry and file links."""

    symmetry = {
        field: structure["attributes"][field]
        for field in SYMMETRY_RESPONSE_FIELDS
        if field in structure["attributes"]
    }
    adapted = Structure(_without_symmetry_fields(structure)).as_dict
    adapted["attributes"].update(symmetry)
    files = structure.get("relationships", {}).get("files")
    if files is not None:
        adapted.setdefault("relationships", {})["files"] = files
    return adapted


def _as_pymatgen(structure: dict):
    """Convert geometry without revalidating provider-specific symmetry syntax."""

    return Structure(_without_symmetry_fields(structure)).as_pymatgen


def _cod_cif_name(structure: dict) -> str | None:
    self_url = str(structure.get("links", {}).get("self", ""))
    if "crystallography.net/cod/optimade/" not in self_url:
        return None

    files = structure.get("relationships", {}).get("files", {}).get("data", [])
    for entry in files:
        name = str(entry.get("id", ""))
        if re.fullmatch(r"\d+\.cif", name):
            return name
    return None


def _cod_topas_str(structure: dict) -> str | None:
    cif_name = _cod_cif_name(structure)
    if cif_name is None:
        return None

    url = f"{COD_CIF_BASE}/{cif_name}"
    try:
        with urlopen(url, timeout=30) as response:
            cif_bytes = response.read()
    except OSError as exc:
        raise ModelRetry(f"Could not download {url}: {exc}") from exc

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / cif_name
        path.write_bytes(cif_bytes)
        text, warnings = cif_to_str(path)

    output = f"' Source CIF: {url}\n{text}"
    if warnings:
        output += "\n\n' Conversion warnings:\n" + "\n".join(
            f"' - {warning}" for warning in warnings
        )
    return output


def get_optimade_structures(
    elements: list[str] | None = None,
    formula: str | None = None,
    query: str | None = None,
    database: Literal["cod", "mp", "oqmd"] = "cod",
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
    client = OptimadeClient(endpoint, use_async=False)

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

    if database == "cod":
        # COD's unversioned endpoint currently resolves to OPTIMADE v1.1, which
        # predates the standard symmetry fields. Use v1.3 explicitly, while
        # retaining OptimadeClient's parsing, pagination, and error handling.
        response_fields.extend(SYMMETRY_RESPONSE_FIELDS)
        query_url = (
            f"{endpoint.rstrip('/')}/{COD_OPTIMADE_VERSION}/structures?"
            + urlencode(
                {
                    "filter": _filter,
                    "response_fields": ",".join(response_fields),
                }
            )
        )
        results = client.get_one(
            endpoint="structures",
            filter=_filter,
            base_url=endpoint,
            response_fields=response_fields,
            override_url=query_url,
        )
        raw_structures = results[endpoint].asdict()["data"]
    else:
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

    return [_adapt_structure(d) for d in raw_structures]


def _space_group(structure: dict, pmg_structure) -> tuple[str | None, str]:
    """Return deposited symmetry when available, otherwise infer it."""

    attributes = structure.get("attributes", {})
    symbol = attributes.get("space_group_symbol_hermann_mauguin_extended")
    if not symbol:
        symbol = attributes.get("space_group_symbol_hermann_mauguin")
    number = attributes.get("space_group_it_number")
    if symbol or number:
        if symbol and number:
            return f"{symbol} (#{number})", "deposited"
        if symbol:
            return str(symbol), "deposited"
        return f"#{number}", "deposited"

    try:
        return pmg_structure.get_symmetry_dataset()["international"], "inferred"
    except Exception:
        return None, "unavailable"


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
    table.add_column("Source")
    table.add_column("a (Å)", justify="right")
    table.add_column("b (Å)", justify="right")
    table.add_column("c (Å)", justify="right")
    table.add_column("α (°)", justify="right")
    table.add_column("β (°)", justify="right")
    table.add_column("γ (°)", justify="right")
    table.add_column("Disordered?")

    for ind, s in enumerate(structures):
        s = _as_pymatgen(s)
        spacegroup, symmetry_source = _space_group(structures[ind], s)

        table.add_row(
            structures[ind]["id"],
            s.reduced_formula.translate(str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")),
            spacegroup,
            symmetry_source,
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


def print_structure(structure: dict) -> str:
    """Focus in on a single structure and print the lattice, atom positions and space group to
    be used when creating a topas input.

    MUST use all the fields provided by OPTIMADE.

    Paramters:
        structure: An optimade Structure object.

    """
    cod_str = _cod_topas_str(structure)
    if cod_str is not None:
        print(cod_str)
        return cod_str

    pmg = _as_pymatgen(structure)
    attributes = structure.get("attributes", {})
    spacegroup, symmetry_source = _space_group(structure, pmg)
    symmetry = [
        f"Space group: {spacegroup or 'unavailable'} ({symmetry_source})",
        f"Hall symbol: {attributes.get('space_group_symbol_hall')}",
    ]
    operations = attributes.get("space_group_symmetry_operations_xyz")
    if operations:
        symmetry.append("Symmetry operations: " + "; ".join(operations))
    output = "\n".join(symmetry + ["", str(pmg)])
    print(output)
    return output
