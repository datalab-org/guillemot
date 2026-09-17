from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

from guillemot.tools import get_optimade_structures, print_structure
from guillemot.tools.optimade import (
    COD_OPTIMADE_VERSION,
    SYMMETRY_RESPONSE_FIELDS,
    _create_optimade_elements_filter,
    _adapt_structure,
    _sanitize_formula,
    _space_group,
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


def test_cod_uses_latest_version_and_requests_deposited_symmetry():
    endpoint = "https://www.crystallography.net/cod/optimade/"
    record = {"id": "1520983", "attributes": {}}
    query_results = Mock()
    query_results.asdict.return_value = {"data": [record]}

    with (
        patch("guillemot.tools.optimade.OptimadeClient") as client_type,
        patch("guillemot.tools.optimade.Structure") as structure_type,
    ):
        client = client_type.return_value
        client.get_one.return_value = {endpoint: query_results}
        structure_type.return_value.as_dict = record

        assert get_optimade_structures(elements=["Fe", "Sb"], database="cod") == [
            record
        ]

    call = client.get_one.call_args
    assert f"/{COD_OPTIMADE_VERSION}/structures?" in call.kwargs["override_url"]
    assert set(SYMMETRY_RESPONSE_FIELDS).issubset(set(call.kwargs["response_fields"]))


def test_adapter_preserves_nonconforming_deposited_symmetry():
    structure = {
        "id": "1512538",
        "relationships": {"files": {"data": [{"id": "1512538.cif", "type": "files"}]}},
        "attributes": {
            "elements": ["Sb"],
            "space_group_symbol_hermann_mauguin": "R -3 m :R",
            "space_group_it_number": 166,
        },
    }
    adapted_geometry = {
        "id": "1512538",
        "attributes": {"elements": ["Sb"]},
    }

    with patch("guillemot.tools.optimade.Structure") as structure_type:
        structure_type.return_value.as_dict = adapted_geometry
        adapted = _adapt_structure(structure)

    passed_to_adapter = structure_type.call_args.args[0]
    assert "space_group_symbol_hermann_mauguin" not in passed_to_adapter["attributes"]
    assert adapted["attributes"]["space_group_symbol_hermann_mauguin"] == "R -3 m :R"
    assert adapted["attributes"]["space_group_it_number"] == 166
    assert adapted["relationships"]["files"] == structure["relationships"]["files"]


def test_deposited_space_group_takes_precedence_over_inference():
    pmg = Mock()
    structure = {
        "attributes": {
            "space_group_symbol_hermann_mauguin": "P n n m",
            "space_group_symbol_hermann_mauguin_extended": None,
            "space_group_it_number": 58,
        }
    }

    assert _space_group(structure, pmg) == ("P n n m (#58)", "deposited")
    pmg.get_symmetry_dataset.assert_not_called()


def test_space_group_inference_is_an_explicit_fallback():
    pmg = Mock()
    pmg.get_symmetry_dataset.return_value = {"international": "P4/mmm"}

    assert _space_group({"attributes": {}}, pmg) == ("P4/mmm", "inferred")


def test_cod_structure_prints_topas_str_from_linked_cif():
    cif = Path(__file__).parent / "fixtures" / "cod-1520983.cif"
    structure = {
        "id": "1520983",
        "links": {
            "self": "https://www.crystallography.net/cod/optimade/v1.3.0/structures/1520983"
        },
        "relationships": {"files": {"data": [{"id": "1520983.cif", "type": "files"}]}},
    }

    with patch(
        "guillemot.tools.optimade.urlopen",
        return_value=BytesIO(cif.read_bytes()),
    ) as download:
        output = print_structure(structure)

    download.assert_called_once_with(
        "https://www.crystallography.net/cod/1520983.cif", timeout=30
    )
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
