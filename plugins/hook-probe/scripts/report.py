#!/usr/bin/env python3
"""Отчёт: какие hook-события сработали в текущей среде и что видел хук вокруг себя."""

import json
import os
import sys
from collections import Counter, defaultdict

LOG = os.environ.get("HOOKPROBE_LOG") or os.path.join(
    os.path.expanduser("~"), ".hook-probe", "hook-probe.jsonl"
)

EXPECTED = ["SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse",
            "Notification", "Stop", "SubagentStart", "SubagentStop",
            "PreCompact", "SessionEnd"]


def main() -> int:
    if not os.path.exists(LOG):
        print(f"Лог не создан: {LOG}")
        print("Вывод: ни один хук плагина не запускался в этой среде.")
        return 1

    rows = []
    for line in open(LOG, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    if not rows:
        print(f"Лог пуст: {LOG}")
        return 1

    counts = Counter(r["event"] for r in rows)
    effects = defaultdict(Counter)
    for r in rows:
        effects[r["event"]][r.get("effect", "?")] += 1

    env = rows[-1].get("environment", {})
    print(f"Лог: {LOG} · записей: {len(rows)} · сессий: {len({r.get('session_id') for r in rows})}")
    print(f"Среда: host={env.get('host')} user={env.get('user')} cwd={env.get('cwd')}")
    print(f"        {env.get('platform')} · python {env.get('python')}")
    ce = env.get("claude_env") or {}
    print(f"CLAUDE_* переменные ({len(ce)}):")
    for k, v in ce.items():
        print(f"  {k}={v}")
    print()
    print(f"{'событие':<18}{'статус':<12}{'раз':>4}  эффекты")
    print("-" * 64)
    for ev in EXPECTED:
        n = counts.get(ev, 0)
        eff = ", ".join(f"{k}×{v}" for k, v in effects[ev].items()) if n else "—"
        print(f"{ev:<18}{'сработал' if n else 'НЕ виден':<12}{n:>4}  {eff}")

    extra = sorted(set(counts) - set(EXPECTED))
    if extra:
        print("\nНеожиданные события:", ", ".join(extra))
    missing = [e for e in EXPECTED if not counts.get(e)]
    print("\nИтог:", "все события зафиксированы" if not missing else "не сработали: " + ", ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
