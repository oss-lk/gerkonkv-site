from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rescore_full_opticks_prime_notation import _summary_text  # noqa: E402


def test_prime_rescore_summary_is_derived_from_current_input_counts() -> None:
    text = _summary_text(
        beam6_prior=[101, 202, 303],
        beam6_invalidated=[{"planned_sequence": 202}],
        staged_prior=[404, 505],
        staged_invalidated=[{"planned_sequence": 505}],
        residual_prime_rows=[
            {"planned_sequence": 606},
            {"planned_sequence": 707},
            {"planned_sequence": 808},
        ],
    )
    assert text == (
        "prime-notation rescore audited 3 beam6 and 2 staged selected rescues; "
        "invalidated 1 beam6 and 1 staged rescues; "
        "3 unresolved staged residuals contain numeric prime notation"
    )
    for legacy_sequence in (745, 638, 2336):
        assert str(legacy_sequence) not in text
