"""Turning a TOPAS parse error into something the agent can act on.

The outputs quoted here are real: they are what TOPAS 6 returned during the FeSb
session, where the agent misread one of them and spent an extra remote run removing
an `@` from the wrong line.
"""

import textwrap

from guillemot.tools.topas import _inp_excerpt

# `scale @ 1.0E-4` is written on line 41 but reported as line 42: TOPAS names the
# point where its parser gave up, not the mistake.
SCALE_ERROR = textwrap.dedent(
    """\
    *** Error loading sstring_in
        at LINE 42
        See log file c:\\users\\group_user\\topas_6\\tc.log

    *** Error at: 1.0E-4
        Maybe an equations starting with an equal sign and
        ending in a semicolon is what is meant.
    """
)

# `Phase_Density_g_on_cm3( @ ... )` on line 43, reported exactly.
DENSITY_ERROR = SCALE_ERROR.replace("at LINE 42", "at LINE 43").replace(
    "*** Error at: 1.0E-4", "*** Error at: @"
)


def _inp_lines() -> str:
    body = [f"line {n}" for n in range(1, 41)]
    body += [
        "\t\tscale @  1.0E-4",
        "\t\tr_bragg  1.0",
        "\t\tPhase_Density_g_on_cm3( @  15.6 )",
        '\t\tOut_CIF_STR("FeSb.cif")',
    ]
    return "\n".join(body)


def test_reported_line_is_marked_and_quoted():
    excerpt = _inp_excerpt(_inp_lines(), SCALE_ERROR, "FeSb_riet_01.inp")

    assert "FeSb_riet_01.inp at line 42" in excerpt
    assert "on the token `1.0E-4`" in excerpt
    assert "> 42 | \t\tr_bragg  1.0" in excerpt


def test_the_real_culprit_is_marked_when_the_line_number_is_off_by_one():
    """The token is the reliable pointer when the line number is not."""
    excerpt = _inp_excerpt(_inp_lines(), SCALE_ERROR, "FeSb_riet_01.inp")

    assert "* 41 | \t\tscale @  1.0E-4" in excerpt


def test_a_single_character_token_is_named_but_not_marked():
    """`@` appears on half the lines of an .inp; marking them all is just noise."""
    excerpt = _inp_excerpt(_inp_lines(), DENSITY_ERROR, "FeSb_riet_02.inp")

    assert "on the token `@`" in excerpt
    assert "> 43 | \t\tPhase_Density_g_on_cm3( @  15.6 )" in excerpt
    assert "*" not in excerpt


def test_context_window_surrounds_the_reported_line():
    excerpt = _inp_excerpt(_inp_lines(), SCALE_ERROR, "x.inp", context=2)
    numbers = [
        line.split("|")[0].strip(" >*") for line in excerpt.splitlines() if "|" in line
    ]

    assert numbers == ["40", "41", "42", "43", "44"]


def test_window_is_clipped_at_the_ends_of_the_file():
    excerpt = _inp_excerpt("only one line\n", "at LINE 1\n", "x.inp")

    assert "> 1 | only one line" in excerpt


def test_no_line_number_means_no_excerpt():
    assert _inp_excerpt(_inp_lines(), "Abnormal program termination.", "x.inp") == ""


def test_a_line_number_past_the_end_of_the_file_is_ignored():
    """Better silence than an excerpt of a file the number cannot refer to."""
    assert _inp_excerpt(_inp_lines(), "    at LINE 9999\n", "x.inp") == ""


def test_unreadable_file_is_not_fatal():
    assert _inp_excerpt("", SCALE_ERROR, "x.inp") == ""
