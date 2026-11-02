from eval.run import run_golden


def test_fr_020_golden_alignment_at_least_98_percent():
    """FR-020：20 单基准对齐率必须达到 98%（当前为 synthetic stand-in）。"""
    rate, diffs = run_golden()
    assert rate >= 98.0
    assert diffs == []
