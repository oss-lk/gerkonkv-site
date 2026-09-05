from pathlib import Path

import pytest

from rocketdict_workbench.cli import parser


def test_generic_upstream_cli_exposes_all_pre_gate_controls() -> None:
    cases = [
        (["product-run-discover-upstream", "/tmp/p", "--state", "/tmp/run.json", "--stage", "10"], "product-run-discover-upstream"),
        (["product-run-bind-upstream", "/tmp/p", "--state", "/tmp/run.json", "--stage", "12", "--operation", "product.stage12.run"], "product-run-bind-upstream"),
        (["product-run-prove-upstream", "/tmp/p", "--state", "/tmp/run.json", "--stage", "14"], "product-run-prove-upstream"),
        (["product-run-plan-upstream", "/tmp/p", "--state", "/tmp/run.json", "--stage", "8"], "product-run-plan-upstream"),
        (["product-run-execute-upstream", "/tmp/p", "--state", "/tmp/run.json", "--stage", "10"], "product-run-execute-upstream"),
    ]
    for argv, command in cases:
        args = parser().parse_args(argv)
        assert args.command == command
        assert args.root == Path("/tmp/p")
        assert args.state == Path("/tmp/run.json")
        assert args.stage in {8, 10, 12, 14}


def test_advance_upstream_cli_supports_resumable_stage_cap() -> None:
    args = parser().parse_args([
        "product-run-advance-upstream",
        "/tmp/project",
        "--state",
        "/tmp/product-run.json",
        "--max-stages",
        "2",
    ])
    assert args.command == "product-run-advance-upstream"
    assert args.state == Path("/tmp/product-run.json")
    assert args.max_stages == 2


def test_generic_upstream_cli_cannot_select_post_gate_stage() -> None:
    with pytest.raises(SystemExit):
        parser().parse_args([
            "product-run-execute-upstream",
            "/tmp/project",
            "--state",
            "/tmp/product-run.json",
            "--stage",
            "16",
        ])
