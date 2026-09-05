from pathlib import Path

from rocketdict_workbench.cli import parser


def test_stage8_binding_cli_requires_state_and_operation() -> None:
    args = parser().parse_args([
        "product-run-bind-stage8",
        "/tmp/project",
        "--state",
        "/tmp/product-run.json",
        "--operation",
        "product.stage8.run",
    ])
    assert args.command == "product-run-bind-stage8"
    assert args.root == Path("/tmp/project")
    assert args.state == Path("/tmp/product-run.json")
    assert args.operation == "product.stage8.run"
