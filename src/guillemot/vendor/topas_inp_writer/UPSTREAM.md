# topas-inp-writer

Vendored from https://github.com/johnsoevans/topas-inp-writer at commit
`d728c821b6a9aa3d7ecca548bad488efd50cc0c9`.

Included files:

- `scripts/cif_to_str.py`
- `scripts/symmetry_utils.py`

The imports between these files were changed to package-relative imports. Local
TOPAS discovery and `sgcom6.exe` execution were removed; missing symmetry now
produces a warning for the agent to handle on the remote TOPAS host. Scattering
species are checked against the bundled `atmscat.txt`. Conversion defaults to
one isotropic `beq` per site, with an explicit option to preserve ADPs.
That file is the copy distributed in TOPAS Academic 7 and in the public
TOPAS Academic 8 skeleton at https://topas-academic.com/ta81.zip.
The upstream MIT license is included in `LICENSE`.
