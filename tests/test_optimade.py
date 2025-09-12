from guillemot.tools import get_optimade_cifs
from guillemot.tools.optimade import _create_optimade_elements_filter, _sanitize_formula


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


def test_optimade_getter():
    antimony = get_optimade_cifs(["Sb"], database="mp")
    assert len(antimony) == 14

    bismuth_antimonides = get_optimade_cifs(elements=["Bi", "Sb"], database="mp")
    assert len(bismuth_antimonides) == 2

    bismuth_antimonides = get_optimade_cifs(elements=["Bi", "Sb"], database="mp")
    assert len(bismuth_antimonides) == 2

    sodium_cobalt_oxies = get_optimade_cifs(formula="NaCoO2", database="mp")
    assert len(sodium_cobalt_oxies) == 9

    bismuth_antimonides = get_optimade_cifs(elements=["Sb"], database="cod")
    assert len(bismuth_antimonides) == 26
