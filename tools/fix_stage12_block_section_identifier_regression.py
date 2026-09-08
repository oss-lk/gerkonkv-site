from pathlib import Path

path = Path("rocketdict-product-core/tests/test_translation_stage_structural_labels.py")
text = path.read_text(encoding="utf-8")
old = 'assert PLANNER_CONTRACT == "rocketdict-stage12-protected-split/7"'
new = 'assert PLANNER_CONTRACT == "rocketdict-stage12-protected-split/8"'
if text.count(old) != 1:
    raise RuntimeError(f"expected one planner-v7 regression assertion, found {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("structural-label planner regression updated to v8")
