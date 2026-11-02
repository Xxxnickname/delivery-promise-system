"""交付门禁检查：测试、G2 自检、22 场景、20 单基准与健康检查。"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> tuple[int, str]:
    """执行子命令并合并输出；失败也继续汇总。"""
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, encoding="utf-8")
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def health() -> tuple[bool, str]:
    """检查 8003 健康接口；服务未启动不影响离线门禁，但会标为未通过。"""
    try:
        with urllib.request.urlopen("http://127.0.0.1:8003/health", timeout=3) as response:
            return response.status == 200, response.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def main() -> int:
    checks = []
    commands = [
        ("pytest", [sys.executable, "-m", "pytest", "-q"]),
        ("g2_check", [sys.executable, "scripts/g2_check.py"]),
        ("acceptance_22", [sys.executable, "scripts/acceptance.py"]),
        ("golden_20", [sys.executable, "eval/run.py", "--golden"]),
    ]
    for name, command in commands:
        code, output = run(command)
        checks.append({"name": name, "ok": code == 0, "exit": code, "tail": "\n".join(output.splitlines()[-6:])})
    healthy, detail = health()
    checks.append({"name": "health_8003", "ok": healthy, "detail": detail[:200]})

    lines = ["# DoD 检查报告", "", f"- 检查时间：{__import__('datetime').datetime.now().isoformat(timespec='seconds')}", ""]
    lines.append("| 检查项 | 结果 |")
    lines.append("|---|---|")
    for item in checks:
        lines.append(f"| {item['name']} | {'PASS' if item['ok'] else 'FAIL'} |")
    lines.append("")
    for item in checks:
        lines.append(f"## {item['name']}")
        lines.append("")
        lines.append("```text")
        lines.append(item.get("tail") or item.get("detail") or "")
        lines.append("```")
        lines.append("")
    (ROOT / "reports" / "dod.md").write_text("\n".join(lines), encoding="utf-8")
    passed = all(item["ok"] for item in checks)
    print(json.dumps({"passed": passed, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
