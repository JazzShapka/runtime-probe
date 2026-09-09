#!/usr/bin/env python3
"""
hook-probe — зонд жизненного цикла хуков, доставляемый как плагин.

Работает там, где живёт сессия (в т.ч. в облачной песочнице Cowork):
лог пишется в $HOME/.hook-probe/hook-probe.jsonl, а не рядом с плагином —
каталог плагина может быть только для чтения.

Делает три вещи:
  1) фиксирует факт срабатывания события;
  2) снимает срез окружения (env CLAUDE_*, cwd, платформа) — разведка среды;
  3) возвращает видимый эффект: кодовое слово в контекст либо deny/ask на Bash.

Вызов: probe.py <EventName>
"""

import json
import os
import platform
import sys
from datetime import datetime, timezone

LOG = os.environ.get("HOOKPROBE_LOG") or os.path.join(
    os.path.expanduser("~"), ".hook-probe", "hook-probe.jsonl"
)

CODE = {
    "SessionStart": "HOOKPROBE-SESSIONSTART-OK",
    "UserPromptSubmit": "HOOKPROBE-PROMPT-OK",
    "PreToolUse": "HOOKPROBE-PRETOOL-OK",
    "PostToolUse": "HOOKPROBE-POSTTOOL-OK",
}

DENY_MARK = "HOOKPROBE_DENY"
ASK_MARK = "HOOKPROBE_ASK"


def read_payload() -> dict:
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {"_unparsed_stdin": raw[:2000]}


def environment() -> dict:
    """Срез среды: что хук вообще видит вокруг себя."""
    return {
        "claude_env": {k: v for k, v in sorted(os.environ.items()) if k.startswith("CLAUDE")},
        "cwd": os.getcwd(),
        "home": os.path.expanduser("~"),
        "user": os.environ.get("USER") or os.environ.get("LOGNAME"),
        "host": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
    }


def log(event: str, payload: dict, effect: str) -> None:
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    cmd = ""
    if isinstance(payload.get("tool_input"), dict):
        cmd = str(payload["tool_input"].get("command", ""))[:200]
    record = {
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "event": event,
        "effect": effect,
        "tool": payload.get("tool_name"),
        "command": cmd,
        "session_id": payload.get("session_id"),
        "payload_keys": sorted(payload.keys()),
        "environment": environment(),
        "payload": payload,
    }
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def emit(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False))


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else "Unknown"
    payload = read_payload()

    if event in ("SessionStart", "UserPromptSubmit"):
        log(event, payload, "additionalContext")
        emit({
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": (
                    f"[hook-probe] {CODE[event]}. Лог зонда: {LOG}. "
                    "Если пользователь спрашивает про хуки — назови это кодовое слово."
                ),
            }
        })
        return 0

    if event == "PreToolUse":
        cmd = ""
        if isinstance(payload.get("tool_input"), dict):
            cmd = str(payload["tool_input"].get("command", ""))
        if DENY_MARK in cmd:
            log(event, payload, "deny")
            emit({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "[hook-probe] заблокировано хуком — HOOKPROBE-DENY-OK",
                }
            })
            return 0
        if ASK_MARK in cmd:
            log(event, payload, "ask")
            emit({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": "[hook-probe] хук требует подтверждения — HOOKPROBE-ASK-OK",
                }
            })
            return 0
        log(event, payload, "additionalContext")
        emit({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"[hook-probe] {CODE['PreToolUse']}",
            }
        })
        return 0

    if event == "PostToolUse":
        log(event, payload, "additionalContext")
        emit({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"[hook-probe] {CODE['PostToolUse']}",
            }
        })
        return 0

    log(event, payload, "log-only")
    emit({"systemMessage": f"[hook-probe] сработал {event}"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
