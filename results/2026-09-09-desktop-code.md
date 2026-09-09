# Claude Desktop, режим Code · 09.09.2026

Каналы доставки: **оба сразу** — плагин и `.claude/settings.json` открытой папки. Каждое событие
срабатывает дважды, по разу от каждого источника; в логи пишут раздельно, поэтому источники различимы.

| Событие | Результат |
|---|---|
| `SessionStart` | ✅ |
| `UserPromptSubmit` | ✅ |
| `PreToolUse` / `PostToolUse` | ✅ и на Bash, и на Agent |
| `Stop`, `SubagentStop`, `SessionEnd` | ✅ |
| `SubagentStart` | ✅ — при явном запуске субагента даёт цепочку `PreToolUse:Agent → SubagentStart → SubagentStop → PostToolUse:Agent` |
| `Notification`, `PreCompact` | ⚪️ повода не возникло |
| `deny` | ✅ вызов реально заблокирован |
| `ask` | ✅ диалог показан пользователю (агент его снова не увидел) |

**Особенности среды:** `CLAUDE_CODE_ENTRYPOINT=claude-desktop`; плагин копируется в сессионную папку
(`~/.config/Claude/local-agent-mode-sessions/.../rpm/plugin_*`, данные — `~/.claude/plugins/data/<name>-inline`);
на один чат стартует несколько дочерних сессий (`CLAUDE_CODE_CHILD_SESSION=1`), поэтому `SessionStart`
и `SessionEnd` в логе кратны их числу.
