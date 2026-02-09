"""Export Claude Code JSONL conversation transcript to readable Markdown."""

import json
import sys
from pathlib import Path

JSONL_PATH = Path(
    "/Users/evnchn/.claude/projects/-Users-evnchn-ClaudeCodeCV/"
    "fcc7244b-bf36-4e50-98f9-6b824a681fbc.jsonl"
)
ROOT = Path(__file__).parent.parent
OUTPUT_PATH = ROOT / "conversation_log.md"


def extract_text_from_content(content):
    """Extract readable text from message content (string or list of blocks)."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, dict):
            btype = block.get("type", "")
            if btype == "text":
                parts.append(block.get("text", ""))
            elif btype == "tool_use":
                name = block.get("name", "unknown")
                inp = block.get("input", {})
                # Summarize tool calls
                if name == "Read":
                    parts.append(f"**[Tool: Read** `{inp.get('file_path', '')}`**]**")
                elif name == "Write":
                    fp = inp.get("file_path", "")
                    content_preview = inp.get("content", "")[:200]
                    parts.append(
                        f"**[Tool: Write** `{fp}`**]**\n"
                        f"<details><summary>Content preview</summary>\n\n"
                        f"```\n{content_preview}...\n```\n</details>"
                    )
                elif name == "Edit":
                    fp = inp.get("file_path", "")
                    old = inp.get("old_string", "")[:100]
                    new = inp.get("new_string", "")[:100]
                    parts.append(
                        f"**[Tool: Edit** `{fp}`**]**\n"
                        f"Old: `{old}`\nNew: `{new}`"
                    )
                elif name == "Bash":
                    cmd = inp.get("command", "")
                    desc = inp.get("description", "")
                    parts.append(
                        f"**[Tool: Bash]** {desc}\n```bash\n{cmd}\n```"
                    )
                elif name == "Glob":
                    parts.append(
                        f"**[Tool: Glob** `{inp.get('pattern', '')}`**]**"
                    )
                elif name == "Grep":
                    parts.append(
                        f"**[Tool: Grep** `{inp.get('pattern', '')}`**]**"
                    )
                elif name == "WebSearch":
                    parts.append(
                        f"**[Tool: WebSearch** `{inp.get('query', '')}`**]**"
                    )
                elif name == "WebFetch":
                    parts.append(
                        f"**[Tool: WebFetch** `{inp.get('url', '')}`**]**"
                    )
                elif name == "Task":
                    desc = inp.get("description", "")
                    prompt_preview = inp.get("prompt", "")[:300]
                    parts.append(
                        f"**[Tool: Task — {desc}]**\n"
                        f"<details><summary>Prompt</summary>\n\n"
                        f"{prompt_preview}...\n</details>"
                    )
                elif name == "TodoWrite":
                    todos = inp.get("todos", [])
                    todo_lines = []
                    for t in todos:
                        status = t.get("status", "")
                        icon = {"completed": "x", "in_progress": "~", "pending": " "}.get(status, " ")
                        todo_lines.append(f"  - [{icon}] {t.get('content', '')}")
                    parts.append(f"**[Tool: TodoWrite]**\n" + "\n".join(todo_lines))
                elif name == "AskUserQuestion":
                    qs = inp.get("questions", [])
                    for q in qs:
                        parts.append(f"**[Tool: AskUserQuestion]** {q.get('question', '')}")
                else:
                    parts.append(f"**[Tool: {name}]** {json.dumps(inp)[:200]}")
            elif btype == "tool_result":
                # Tool results — include a summary
                result_content = block.get("content", "")
                if isinstance(result_content, list):
                    for rb in result_content:
                        if isinstance(rb, dict) and rb.get("type") == "text":
                            text = rb.get("text", "")
                            if len(text) > 500:
                                text = text[:500] + f"\n... [{len(text)} chars total]"
                            parts.append(
                                f"<details><summary>Tool result</summary>\n\n"
                                f"```\n{text}\n```\n</details>"
                            )
                elif isinstance(result_content, str) and result_content:
                    if len(result_content) > 500:
                        result_content = result_content[:500] + f"\n... [{len(result_content)} chars total]"
                    parts.append(
                        f"<details><summary>Tool result</summary>\n\n"
                        f"```\n{result_content}\n```\n</details>"
                    )
            elif btype == "image":
                parts.append("**[Image displayed]**")
    return "\n\n".join(parts)


def main():
    lines = JSONL_PATH.read_text().strip().split("\n")
    print(f"Parsing {len(lines)} JSONL entries...")

    md_parts = [
        "# Claude Code Conversation Log",
        "",
        f"> **Session ID:** `fcc7244b-bf36-4e50-98f9-6b824a681fbc`",
        f"> **Date:** 2026-02-09",
        f"> **Source:** Auto-exported from Claude Code JSONL transcript",
        "",
        "---",
        "",
    ]

    msg_count = 0
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        entry_type = entry.get("type", "")
        message = entry.get("message", {})
        role = message.get("role", "") or entry_type
        content = message.get("content", "")
        timestamp = entry.get("timestamp", "")

        if role == "user" and content:
            msg_count += 1
            text = extract_text_from_content(content)
            if not text.strip():
                continue
            # Filter out system-reminder noise from user messages
            if text.strip().startswith("<system-reminder>") and "user" not in text.lower():
                continue
            md_parts.append(f"## User (#{msg_count}) — {timestamp}")
            md_parts.append("")
            md_parts.append(text)
            md_parts.append("")
            md_parts.append("---")
            md_parts.append("")

        elif role == "assistant" and content:
            text = extract_text_from_content(content)
            if not text.strip():
                continue
            md_parts.append(f"### Assistant — {timestamp}")
            md_parts.append("")
            md_parts.append(text)
            md_parts.append("")
            md_parts.append("---")
            md_parts.append("")

    output = "\n".join(md_parts)
    OUTPUT_PATH.write_text(output, encoding="utf-8")
    print(f"Exported {msg_count} user messages to {OUTPUT_PATH}")
    print(f"File size: {OUTPUT_PATH.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
