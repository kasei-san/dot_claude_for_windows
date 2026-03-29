#!/usr/bin/env python3
"""
PreToolUse hook for Bash tool.
Splits compound commands (&&, ||, ;) and checks if ALL sub-commands
match the allowed prefixes. If so, auto-allows. Otherwise, passes
through to normal permission handling.
"""

import json
import re
import sys

# Allowed command prefixes (derived from settings.local.json)
ALLOWED_PREFIXES = [
    "wmic path",
    "nvidia-smi",
    "powershell.exe",
    "powershell ",
    "python",
    "ls",
    "find",
    "grep",
    "cat",
    "head",
    "tail",
    "wc",
    "file ",
    "which",
    "where",
    "pwd",
    "echo",
    "rg",
    "git status",
    "git log",
    "git diff",
    "git show",
    "git branch",
    "git remote",
    "git tag",
    "git stash",
    "git rev-parse",
    "git config --get",
    "git config --list",
    "git blame",
    "git shortlog",
    "git push",
    "git commit",
    "git checkout",
    "git switch",
    "git add",
    "gh pr list",
    "gh pr view",
    "gh pr diff",
    "gh pr checks",
    "gh issue list",
    "gh issue view",
    "gh repo view",
    "gh run list",
    "gh run view",
    "gh api",
]


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


def is_allowed(cmd: str) -> bool:
    """Check if a single command matches any allowed prefix."""
    cmd_stripped = cmd.strip()
    for prefix in ALLOWED_PREFIXES:
        if cmd_stripped == prefix or cmd_stripped.startswith(prefix + " ") or cmd_stripped.startswith(prefix + "\t"):
            return True
        # Handle case where prefix ends with space (like "file " or "powershell ")
        if prefix.endswith(" ") and cmd_stripped.startswith(prefix):
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

    all_allowed = all(is_allowed(cmd) for cmd in sub_commands)

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
