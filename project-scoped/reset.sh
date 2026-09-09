#!/usr/bin/env bash
# Очистить лог перед новым прогоном.
cd "$(dirname "$0")" && rm -f logs/hook-probe.jsonl && echo "лог очищен"
