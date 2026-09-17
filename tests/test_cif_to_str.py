import math
from pathlib import Path

import pytest

from guillemot.vendor.topas_inp_writer.cif_to_str import adp_to_beq, convert


FIXTURES = Path(__file__).parent / "fixtures"


def convert_cod(cod_id, **kwargs):
    return convert(FIXTURES / f"cod-{cod_id}.cif", **kwargs)


def test_cubic_special_positions():
    output, warnings = convert_cod("1000041")

    assert 'space_group "F_m_-3_m"' in output
    assert "b = Get(a);" in output
    assert "c = Get(a);" in output
    assert "site Na1  num_posns 4  x 0  y 0  z 0  occ Na+1 1" in output
    assert "site Cl1  num_posns 4  x = 1/2;  y = 1/2;  z = 1/2;" in output
    assert output.count("beq @ 1 ") == 2
    assert warnings == []


def test_anisotropic_displacements_are_isotropic_by_default():
    output, warnings = convert_cod("1577381")

    assert 'space_group "P_63_m_c"' in output
    assert "b = Get(a);" in output
    assert "ga 120.0" in output
    assert "site Zn  num_posns 2  x = 1/3;  y = 2/3;  z @ 0" in output
    assert "beq @ 0.513219" in output
    assert "beq @ 0.592176" in output
    assert "u11" not in output
    assert not any("sgcom6" in warning for warning in warnings)


def test_anisotropic_displacement_override():
    output, _ = convert_cod("1577381", use_adps=True)

    assert "u22 = Get(u11);" in output
    assert "u12 = Get(u11) / 2;" in output
    assert " beq " not in output


def test_anisotropic_displacements_can_supply_beq():
    row = {
        "_atom_site_aniso_U_11": "0.01",
        "_atom_site_aniso_U_22": "0.02",
        "_atom_site_aniso_U_33": "0.03",
    }

    assert adp_to_beq(row, (4, 5, 6, 90, 90, 90)) == pytest.approx(
        8 * math.pi**2 * 0.02
    )


def test_pbnm_special_and_general_sites():
    output, warnings = convert_cod("1006141")

    assert 'space_group "P_b_n_m"' in output
    assert "site La1  num_posns 4  x @ -0.0078  y @ 0.049  z = 1/4;" in output
    assert "site Mn1  num_posns 4  x = 1/2;  y 0  z 0" in output
    assert "site O2  num_posns 8  x @ 0.7256  y @ 0.3066  z @ 0.0384" in output
    assert output.count("beq @ 1 ") == 4
    assert warnings == []


def test_partial_occupancy_and_coordinate_tie():
    output, warnings = convert_cod("1532937")

    assert 'space_group "P_63/m_m_c"' in output
    assert "site Na2  num_posns 2  x 0  y 0  z = 1/4;  occ Na+1 0.171" in output
    assert (
        "site Na1  num_posns 6  x = 2 * Get(y);  y @ 0.2885  z = 1/4;  occ Na+1 0.146"
    ) in output
    assert output.count("beq @ 1 ") == 4
    assert not any("sgcom6" in warning for warning in warnings)


def test_rhombohedral_hexagonal_setting():
    output, warnings = convert_cod("1529124")

    assert 'space_group "R_3_m:H"' in output
    assert "b = Get(a);" in output
    assert "ga 120.0" in output
    assert "site Na1  num_posns 3  x 0  y 0  z @ 0.836  occ Na 0.6" in output
    assert output.count("beq @ 1 ") == 4
    assert any("sgcom6.exe on the TOPAS host" in warning for warning in warnings)
