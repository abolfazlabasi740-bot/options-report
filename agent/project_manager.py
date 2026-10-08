#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

import requests

ROOT = Path(os.environ.get("OPTIMUSAI_ROOT", Path.home() / "OptimusAI_V41_LIVE")).expanduser().resolve()
PROVIDER = os.environ.get("OPTIMUSAI_PROVIDER", "local").strip().lower()
MODEL = os.environ.get("OPTIMUSAI_LLM_MODEL", "local").strip()
API_BASE = os.environ.get("OPTIMUSAI_API_BASE", "http://127.0.0.1:8080/v1").strip().rstrip("/")
API_KEY = os.environ.get("OPTIMUSAI_API_KEY", "local").strip()
MAX_OUTPUT = int(os.environ.get("OPTIMUSAI_MAX_OUTPUT_TOKENS", "6000"))
MAX_TURNS = int(os.environ.get("OPTIMUSAI_MAX_TURNS", "24"))
HTTP_TIMEOUT = int(os.environ.get("OPTIMUSAI_HTTP_TIMEOUT", "300"))

SYSTEM = """You are the senior execution agent inside the OptimusAI_V41_LIVE project.
ChatGPT is the project manager. You execute the assigned task locally and return evidence.

Operating rules:
- Inspect relevant files before changing them.
- TSETMC is the single source of truth for market data.
- Never invent, estimate, or impute missing market data.
- Outside TSETMC live hours, use the latest valid snapshot; never force a current-time fetch after close.
- Do not mix old scoring models with the canonical BASE SHARE OPPORTUNITY SCORE V1.
- Do not claim success without executable evidence.
- Prefer complete file replacements over fragile line edits.
- Preserve unrelated user work.
- Never use destructive shell commands.
- After changes, run the narrowest useful verification and inspect git diff/status.
- Commit only verified changes when the task requires implementation.
"""

def _safe_path(path: str) -> Path:
    q = (ROOT / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if q != ROOT and ROOT not in q.parents:
        raise ValueError("path outside project")
    return q

def read_file(path: str, start: int = 1, end: int = 400) -> dict:
    q = _safe_path(path)
    if not q.exists():
        raise FileNotFoundError(str(q))
    lines = q.read_text(encoding="utf-8").splitlines()
    start = max(1, start)
    end = max(start, end)
    return {
        "path": str(q.relative_to(ROOT)),
        "content": "\n".join(lines[start - 1:end]),
        "line_start": start,
        "line_end": min(end, len(lines)),
    }

def write_file(path: str, content: str) -> dict:
    q = _safe_path(path)
    q.parent.mkdir(parents=True, exist_ok=True)
    q.write_text(content, encoding="utf-8")
    return {"path": str(q.relative_to(ROOT)), "bytes": len(content.encode("utf-8"))}

def run_command(command: str, timeout: int = 120) -> dict:
    blocked = (
        "rm -rf", "shutdown", "reboot", "mkfs", "dd ",
        "git reset --hard", "git push --force",
    )
    if any(token in command for token in blocked):
        raise ValueError("blocked destructive command")

    parts = shlex.split(command)
    if not parts:
        raise ValueError("empty command")

    allowed = {"python", "python3", "git", "bash", "sh", "pytest", "pip", "curl"}
    if parts[0] not in allowed:
        raise ValueError(f"command not allowed: {parts[0]}")

    p = subprocess.run(
        parts,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=min(max(1, timeout), 300),
    )
    return {
        "command": command,
        "returncode": p.returncode,
        "stdout": p.stdout[-12000:],
        "stderr": p.stderr[-12000:],
    }

def git_status() -> dict:
    def run(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=60)

    status = run(["git", "status", "--short"])
    branch = run(["git", "branch", "--show-current"])
    head = run(["git", "rev-parse", "HEAD"])
    return {
        "status": status.stdout,
        "branch": branch.stdout.strip(),
        "head": head.stdout.strip(),
        "errors": "\n".join(x.stderr for x in (status, branch, head) if x.stderr),
    }

def git_diff() -> dict:
    p = subprocess.run(
        ["git", "diff", "--"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    return {"returncode": p.returncode, "diff": p.stdout[-30000:], "stderr": p.stderr[-5000:]}

def git_commit(message: str) -> dict:
    safe = " ".join(message.split()).strip()[:120]
    if not safe:
        raise ValueError("empty commit message")

    add = subprocess.run(["git", "add", "-A"], cwd=ROOT, text=True, capture_output=True, timeout=60)
    if add.returncode:
        return {"returncode": add.returncode, "stdout": add.stdout, "stderr": add.stderr}

    commit = subprocess.run(
        ["git", "commit", "-m", safe],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    return {"returncode": commit.returncode, "stdout": commit.stdout, "stderr": commit.stderr}

TOOLS = [
    {"type": "function", "function": {"name": "read_file", "description": "Read a project file. Use before modifying code.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "start": {"type": "integer", "minimum": 1}, "end": {"type": "integer", "minimum": 1}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Write a complete project file for an intentional change.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "run_command", "description": "Run an approved project command for tests, scripts, or diagnostics.", "parameters": {"type": "object", "properties": {"command": {"type": "string"}, "timeout": {"type": "integer", "minimum": 1, "maximum": 300}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "git_status", "description": "Inspect repository state.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "git_diff", "description": "Inspect the current diff before committing.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "git_commit", "description": "Commit verified project changes.", "parameters": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}}},
]

FN = {
    "read_file": read_file,
    "write_file": write_file,
    "run_command": run_command,
    "git_status": git_status,
    "git_diff": git_diff,
    "git_commit": git_commit,
}

def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

def _chat(messages: list[dict[str, Any]]) -> dict[str, Any]:
    if PROVIDER not in {"local", "local_openai", "openai_compatible"}:
        raise RuntimeError(f"Unsupported provider '{PROVIDER}'")
    response = requests.post(
        f"{API_BASE}/chat/completions",
        headers=_headers(),
        json={
            "model": MODEL,
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
            "temperature": 0.1,
            "max_tokens": MAX_OUTPUT,
        },
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()

def main() -> None:
    task = os.environ.get("OPTIMUSAI_TASK", "").strip()
    if not task:
        raise SystemExit("OPTIMUSAI_TASK is required")

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": task},
    ]

    for _ in range(MAX_TURNS):
        data = _chat(messages)
        choice = data["choices"][0]
        message = choice["message"]
        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            print(message.get("content") or "")
            return

        messages.append(message)

        for call in tool_calls:
            function = call.get("function") or {}
            name = function.get("name")
            args = json.loads(function.get("arguments") or "{}")
            if name not in FN:
                payload = {"ok": False, "error": f"unknown tool: {name}"}
            else:
                try:
                    payload = {"ok": True, "result": FN[name](**args)}
                except Exception as exc:
                    payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

            messages.append({
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "content": json.dumps(payload, ensure_ascii=False),
            })

    raise RuntimeError(f"agent tool loop exceeded {MAX_TURNS} turns")

if __name__ == "__main__":
    main()
