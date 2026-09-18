from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from pymatgen.core import Lattice, Structure as PymatgenStructure

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


@pytest.mark.parametrize(
    ("kwargs", "expected_symprec"),
    [({}, 0.1), ({"symprec": 0.2}, 0.2)],
)
def test_computational_structure_writes_symmetrized_cif_and_prints_topas_str(
    tmp_path, monkeypatch, kwargs, expected_symprec
):
    monkeypatch.chdir(tmp_path)
    pmg = PymatgenStructure.from_spacegroup(
        "P-3m1",
        Lattice.hexagonal(3.01, 5.51),
        ["Na", "Co", "O"],
        [[0, 0, 0.5], [0, 0, 0], [1 / 3, 2 / 3, 0.2]],
    )

    with patch("guillemot.tools.optimade.Structure") as adapter:
        adapter.return_value.as_pymatgen = pmg
        output = print_structure(
            {
                "id": "oqmd/123",
                "links": {"self": "https://oqmd.org/optimade/v1/structures/123"},
            },
            **kwargs,
        )

    cif = tmp_path / "oqmd_123.cif"
    assert cif.is_file()
    assert "_symmetry_equiv_pos_as_xyz" in cif.read_text()
    assert f"' Saved CIF: {cif}" in output
    assert (
        f"' Symmetry inferred by pymatgen/spglib (symprec {expected_symprec:g} A"
        in output
    )
    assert 'space_group "P-3m1"' in output
    assert "site Na0  num_posns 1  x 0  y 0  z = 1/2;" in output
    assert "site Co1  num_posns 1  x 0  y 0  z 0" in output
    assert "site O2  num_posns 2  x = 1/3;  y = 2/3;  z @ 0.2" in output
    assert output.count("beq @ 1 min -50 max 51") == 3


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
