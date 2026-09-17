from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from guillemot.tools import get_optimade_structures, print_structure
from guillemot.tools.optimade import (
    _create_optimade_elements_filter,
    _sanitize_formula,
)


def test_elements_filter():
    assert (
        _create_optimade_elements_filter(["Sb"])
        == 'elements HAS "Sb" AND elements LENGTH 1'
    )
    assert (
        _create_optimade_elements_filter(["Sb", "S"])
        == 'elements HAS ALL "Sb","S" AND elements LENGTH 2'
    )

    # no validation of elements is done, so this works too:
    assert (
        _create_optimade_elements_filter(["Sb", "X", "Y"])
        == 'elements HAS ALL "Sb","X","Y" AND elements LENGTH 3'
    )


def test_sanitize_formula():
    assert _sanitize_formula("NaCoO2") == "CoNaO2"
    assert _sanitize_formula("Na1Co1O2") == "CoNaO2"


def test_cod_structure_downloads_and_prints_topas_str(tmp_path, monkeypatch):
    cif = Path(__file__).parent / "fixtures" / "cod-1520983.cif"
    cif_bytes = cif.read_bytes()
    monkeypatch.chdir(tmp_path)
    structure = {
        "id": "1520983",
        "links": {
            "self": "https://www.crystallography.net/cod/optimade/v1.1.0/structures/1520983"
        },
    }

    with patch(
        "guillemot.tools.optimade.urlopen",
        return_value=BytesIO(cif_bytes),
    ) as download:
        output = print_structure(structure)

    download.assert_called_once_with(
        "https://www.crystallography.net/cod/1520983.cif", timeout=30
    )
    assert (tmp_path / "1520983.cif").read_bytes() == cif_bytes
    assert f"' Saved CIF: {tmp_path / '1520983.cif'}" in output
    assert 'space_group "P_n_n_m"' in output
    assert "site Sb1  num_posns 4  x @ 0.1882  y @ 0.6437  z 0" in output
    assert "site Fe1  num_posns 2  x 0  y 0  z 0" in output
    assert "site Sb1_2_555" not in output


def test_optimade_getter():
    antimony = get_optimade_structures(["Sb"], database="mp")
    assert len(antimony) == 14

    bismuth_antimonides = get_optimade_structures(elements=["Bi", "Sb"], database="mp")
    assert len(bismuth_antimonides) == 2

    bismuth_antimonides = get_optimade_structures(elements=["Bi", "Sb"], database="mp")
    assert len(bismuth_antimonides) == 2

    sodium_cobalt_oxies = get_optimade_structures(formula="NaCoO2", database="mp")
    assert len(sodium_cobalt_oxies) == 9

    bismuth_antimonides = get_optimade_structures(elements=["Sb"], database="cod")
    assert len(bismuth_antimonides) == 26
