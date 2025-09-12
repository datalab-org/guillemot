def test_optimade_getter():
    from guillemot.tools import get_optimade_cifs

    antimony = get_optimade_cifs(["Sb"], "mp")
    assert len(antimony) == 14
