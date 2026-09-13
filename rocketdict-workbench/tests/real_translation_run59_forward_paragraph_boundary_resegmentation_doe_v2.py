from __future__ import annotations

"""Corrected run59 forward-boundary DOE launcher.

The original DOE harness used a stale/incorrect database SHA copied from L1.
Canonical run59 artifact evidence proves the actual SQLite SHA below.  All DOE
logic remains in the v1 module; only the immutable artifact identity is repaired.
"""

import real_translation_run59_forward_paragraph_boundary_resegmentation_doe as doe


doe.BASE_DATABASE_SHA256 = "41bafa00619c83b87f55f7e452f8e9e27a1871d601bb5c846d3d561531dbb78d"


if __name__ == "__main__":
    raise SystemExit(doe.main())
