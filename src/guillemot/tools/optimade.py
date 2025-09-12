from typing import Literal
from optimade.client import OptimadeClient
from optimade.adapters import Structure

def get_optimade_cifs(
    elements: list[str], database: Literal["cod", "mp", "oqmd"]
) -> list[str]:
    """
    Perform an OPITIMADE query for a set of elements to a restricted set of databases
    and return the results as a list of CIF strings.

    Parameters:
        elements: A list of element symbols to query for, e.g., ["Li", "C", "O"].
            Will be treated as an OPTIMADE `HAS ONLY` query, i.e., ?filter=elements HAS ONLY "Li", "C", "O",
            or equivalently ?filter=elements HAS ALL "Li", "C", "O" AND elements LENGTH 3.
        database: The database to query, one of "cod" (Crystallography Open Database),
            "mp" (Materials Project), or "oqmd" (Open Quantum Materials Database).

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

    if len(elements) > 1:
        _filter = f'elements HAS ALL "{",".join(elements)}" AND elements LENGTH {len(elements)}'
    else:
        _filter = f'elements HAS "{elements[0]}" AND elements LENGTH 1'

    results = client.get(_filter)

    structures = [
        Structure(d) for d in results["structures"][_filter][endpoint]["data"]
    ]

    return [struct.as_cif for struct in structures]


