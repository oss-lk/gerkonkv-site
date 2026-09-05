from pathlib import Path

from rocketdict_workbench.cli import parser


def test_stage8_execution_cli_commands_require_explicit_state() -> None:
    cases = (
        "product-run-prove-stage8-execution",
        "product-run-plan-stage8",
        "product-run-execute-stage8",
    )
    for command in cases:
        args = parser().parse_args([command, "/tmp/project", "--state", "/tmp/product-run.json"])
        assert args.command == command
        assert args.root == Path("/tmp/project")
        assert args.state == Path("/tmp/product-run.json")
