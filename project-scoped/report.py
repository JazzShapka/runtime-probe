#!/usr/bin/env python3
"""Отчёт стенда: какие события хуков сработали, какие — нет."""

import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "logs", "hook-probe.jsonl")

EXPECTED = [
    "SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse",
    "Notification", "Stop", "SubagentStart", "SubagentStop",
    "PreCompact", "SessionEnd",
]


def main() -> int:
    if not os.path.exists(LOG):
        print("Лог пуст: ни один хук не сработал (или стенд не открыт как рабочая папка).")
        print(f"Ожидался файл: {LOG}")
        return 1

    rows = []
    for line in open(LOG, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except Exception:
                pass

    counts = Counter(r["event"] for r in rows)
    effects = defaultdict(Counter)
    for r in rows:
        effects[r["event"]][r.get("effect", "?")] += 1

    entry = {r["env"].get("CLAUDE_CODE_ENTRYPOINT") for r in rows if r.get("env")}
    sessions = {r.get("session_id") for r in rows if r.get("session_id")}
    print(f"Записей: {len(rows)} · сессий: {len(sessions)} · entrypoint: {', '.join(sorted(x or '—' for x in entry))}")
    print(f"Лог: {LOG}\n")
    print(f"{'событие':<18}{'статус':<12}{'раз':>4}  эффекты")
    print("-" * 64)
    for ev in EXPECTED:
        n = counts.get(ev, 0)
        status = "сработал" if n else "НЕ виден"
        eff = ", ".join(f"{k}×{v}" for k, v in effects[ev].items()) if n else "—"
        print(f"{ev:<18}{status:<12}{n:>4}  {eff}")

    extra = sorted(set(counts) - set(EXPECTED))
    if extra:
        print("\nНеожиданные события:", ", ".join(extra))

    missing = [e for e in EXPECTED if not counts.get(e)]
    print("\nИтог:", "все события зафиксированы" if not missing else "не сработали: " + ", ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
