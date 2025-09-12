
def test_optimade_getter():
    from guillemot.tools import get_optimade_cifs
    from guillemot.tools.optimade import _create_optimade_filter

    # Check filter creator directly
    assert _create_optimade_filter(["Sb"]) == 'elements HAS "Sb" AND elements LENGTH 1'
    assert _create_optimade_filter(["Sb", "S"]) == 'elements HAS ALL "Sb","S" AND elements LENGTH 2'

    # no validation of elements is done, so this works too:
    assert _create_optimade_filter(["Sb", "X", "Y"]) == 'elements HAS ALL "Sb","X","Y" AND elements LENGTH 3'

    antimony = get_optimade_cifs(["Sb"], "mp")
    assert len(antimony) == 14

    bismuth_antimonides = get_optimade_cifs(["Bi", "Sb"], "mp")
    assert len(bismuth_antimonides) == 2
