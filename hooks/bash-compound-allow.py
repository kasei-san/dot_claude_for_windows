#!/usr/bin/env python3
"""
PreToolUse hook for Bash tool.
Splits compound commands (&&, ||, ;) and checks if ALL sub-commands
match the allowed prefixes. If so, auto-allows. Otherwise, passes
through to normal permission handling.

Allowed prefixes are derived from settings.local.json automatically.
"""

import json
import os
import re
import sys


def load_allowed_prefixes() -> list[str]:
    """Load allowed Bash prefixes from settings.local.json."""
    settings_path = os.path.join(os.path.expanduser("~"), ".claude", "settings.local.json")
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    allow_list = settings.get("permissions", {}).get("allow", [])
    prefixes = []
    for entry in allow_list:
        # Match "Bash(prefix:*)" pattern
        m = re.match(r'^Bash\((.+?):\*\)$', entry)
        if m:
            prefixes.append(m.group(1))
    return prefixes


def split_compound_command(cmd: str) -> list[str]:
    """Split command by &&, ||, and ; respecting quoted strings."""
    parts = []
    current = []
    i = 0
    in_single_quote = False
    in_double_quote = False

    while i < len(cmd):
        c = cmd[i]

        if c == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            current.append(c)
        elif c == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            current.append(c)
        elif not in_single_quote and not in_double_quote:
            if c == '&' and i + 1 < len(cmd) and cmd[i + 1] == '&':
                parts.append(''.join(current).strip())
                current = []
                i += 2
                continue
            elif c == '|' and i + 1 < len(cmd) and cmd[i + 1] == '|':
                parts.append(''.join(current).strip())
                current = []
                i += 2
                continue
            elif c == ';':
                parts.append(''.join(current).strip())
                current = []
                i += 1
                continue
            else:
                current.append(c)
        else:
            current.append(c)
        i += 1

    remaining = ''.join(current).strip()
    if remaining:
        parts.append(remaining)

    return [p for p in parts if p]


def is_allowed(cmd: str, prefixes: list[str]) -> bool:
    """Check if a single command matches any allowed prefix."""
    cmd_stripped = cmd.strip()
    for prefix in prefixes:
        if cmd_stripped == prefix or cmd_stripped.startswith(prefix + " ") or cmd_stripped.startswith(prefix + "\t"):
            return True
    return False


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    command = input_data.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    sub_commands = split_compound_command(command)

    if not sub_commands:
        sys.exit(0)

    prefixes = load_allowed_prefixes()
    if not prefixes:
        sys.exit(0)

    all_allowed = all(is_allowed(cmd, prefixes) for cmd in sub_commands)

    if all_allowed:
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "All sub-commands in compound command are allowed",
            }
        }
        json.dump(result, sys.stdout)

    sys.exit(0)


if __name__ == "__main__":
    main()
