#!/usr/bin/env python3
"""
Универсальный зонд для проверки хуков в любой обвязке Claude (CLI, Cowork, IDE).

Один скрипт вешается на все события. Делает две вещи:
  1) пишет факт срабатывания в logs/hook-probe.jsonl (машинная проверка);
  2) возвращает видимый в чате эффект — кодовое слово, systemMessage или deny
     (проверка, что вывод хука реально доходит до модели и до движка разрешений).

Вызов: probe.py <EventName>
Событие берём из аргумента, а не только из payload: часть обвязок
не кладёт hook_event_name в stdin.
"""

import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "logs", "hook-probe.jsonl")

# Кодовые слова: если видишь их в чате — вывод хука дошёл до модели.
CODE = {
    "SessionStart": "HOOKPROBE-SESSIONSTART-OK",
    "UserPromptSubmit": "HOOKPROBE-PROMPT-OK",
    "PreToolUse": "HOOKPROBE-PRETOOL-OK",
    "PostToolUse": "HOOKPROBE-POSTTOOL-OK",
}

# Маркеры в команде Bash, которыми тест управляет поведением хука.
DENY_MARK = "HOOKPROBE_DENY"      # PreToolUse обязан заблокировать вызов
ASK_MARK = "HOOKPROBE_ASK"        # PreToolUse обязан спросить подтверждение


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


def log(event: str, payload: dict, effect: str) -> None:
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    tool = payload.get("tool_name")
    cmd = ""
    if isinstance(payload.get("tool_input"), dict):
        cmd = str(payload["tool_input"].get("command", ""))[:200]
    record = {
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "event": event,
        "effect": effect,
        "tool": tool,
        "command": cmd,
        "session_id": payload.get("session_id"),
        "cwd": payload.get("cwd") or os.getcwd(),
        "payload_keys": sorted(payload.keys()),
        "env": {
            "CLAUDE_PROJECT_DIR": os.environ.get("CLAUDE_PROJECT_DIR"),
            "CLAUDE_CODE_ENTRYPOINT": os.environ.get("CLAUDE_CODE_ENTRYPOINT"),
        },
        "payload": payload,
    }
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def emit(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False))


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else "Unknown"
    payload = read_payload()
    effect = "log-only"

    if event in ("SessionStart", "UserPromptSubmit"):
        effect = "additionalContext"
        log(event, payload, effect)
        emit({
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": (
                    f"[hook-probe] {CODE[event]}. "
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
            effect = "deny"
            log(event, payload, effect)
            emit({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "[hook-probe] заблокировано хуком — HOOKPROBE-DENY-OK",
                }
            })
            return 0
        if ASK_MARK in cmd:
            effect = "ask"
            log(event, payload, effect)
            emit({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": "[hook-probe] хук требует подтверждения — HOOKPROBE-ASK-OK",
                }
            })
            return 0
        effect = "additionalContext"
        log(event, payload, effect)
        emit({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"[hook-probe] {CODE['PreToolUse']}",
            }
        })
        return 0

    if event == "PostToolUse":
        effect = "additionalContext"
        log(event, payload, effect)
        emit({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"[hook-probe] {CODE['PostToolUse']}",
            }
        })
        return 0

    # Stop, SubagentStop, SubagentStart, Notification, PreCompact, SessionEnd —
    # только фиксируем факт, ничего не блокируем.
    log(event, payload, effect)
    emit({"systemMessage": f"[hook-probe] сработал {event}"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
