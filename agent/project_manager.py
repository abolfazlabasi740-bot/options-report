#!/usr/bin/env python3
from __future__ import annotations
import json, os, subprocess, shlex
from pathlib import Path
from typing import Any
from openai import OpenAI

ROOT = Path(os.environ.get("OPTIMUSAI_ROOT", Path.home() / "OptimusAI_V41_LIVE")).expanduser().resolve()
MODEL = os.environ.get("OPTIMUSAI_LLM_MODEL", "gpt-6-luna")
MAX_OUTPUT = int(os.environ.get("OPTIMUSAI_MAX_OUTPUT_TOKENS", "6000"))

SYSTEM = """You are the execution agent inside the OptimusAI_V41_LIVE project.
You are not the project manager; ChatGPT is the project manager. You are the senior implementation agent.
Work directly in the project, inspect before changing, make complete safe changes, run verification, and report evidence.
Rules:
- TSETMC is the single source of truth for market data.
- Never invent or impute missing market data.
- Outside TSETMC live hours use the latest valid snapshot; never force a current-time fetch after close.
- Do not mix old scoring models with the canonical BASE SHARE OPPORTUNITY SCORE V1.
- Do not claim success without executable evidence.
- Prefer complete file replacements over fragile line edits.
- Do not delete unrelated work.
- Never use destructive shell commands.
- After changes, run the narrowest useful tests and git diff/status.
"""

def _safe_path(p: str) -> Path:
    q = (ROOT / p).resolve() if not Path(p).is_absolute() else Path(p).resolve()
    if q != ROOT and ROOT not in q.parents:
        raise ValueError("path outside project")
    return q

def read_file(path: str, start: int = 1, end: int = 400) -> dict:
    q = _safe_path(path)
    lines = q.read_text(encoding="utf-8").splitlines()
    return {"path": str(q.relative_to(ROOT)), "content": "\n".join(lines[start-1:end]), "line_start": start, "line_end": min(end,len(lines))}

def write_file(path: str, content: str) -> dict:
    q = _safe_path(path)
    q.parent.mkdir(parents=True, exist_ok=True)
    q.write_text(content, encoding="utf-8")
    return {"path": str(q.relative_to(ROOT)), "bytes": len(content.encode("utf-8"))}

def run_command(command: str, timeout: int = 120) -> dict:
    blocked = ["rm -rf","shutdown","reboot","mkfs","dd ","git reset --hard","git push --force"]
    if any(x in command for x in blocked):
        raise ValueError("blocked destructive command")
    parts = shlex.split(command)
    if not parts:
        raise ValueError("empty command")
    allowed = {"python","python3","git","bash","sh","pytest","pip"}
    if parts[0] not in allowed:
        raise ValueError(f"command not allowed: {parts[0]}")
    p = subprocess.run(parts, cwd=ROOT, text=True, capture_output=True, timeout=min(timeout,300))
    return {"command": command, "returncode": p.returncode, "stdout": p.stdout[-12000:], "stderr": p.stderr[-12000:]}

def git_status() -> dict:
    return run_command("git status --short && git branch --show-current && git rev-parse HEAD")

def git_diff() -> dict:
    return run_command("git diff --")

def git_commit(message: str) -> dict:
    safe = message.replace("\n"," ").strip()[:120]
    return run_command(f"git add -A && git commit -m {shlex.quote(safe)}")

TOOLS = [
 {"type":"function","name":"read_file","description":"Read a project file. Use before modifying code.","parameters":{"type":"object","properties":{"path":{"type":"string"},"start":{"type":"integer"},"end":{"type":"integer"}},"required":["path"]}},
 {"type":"function","name":"write_file","description":"Write a complete project file. Use for intentional code/config changes.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}},
 {"type":"function","name":"run_command","description":"Run an approved project command for tests, scripts, or diagnostics.","parameters":{"type":"object","properties":{"command":{"type":"string"},"timeout":{"type":"integer"}},"required":["command"]}},
 {"type":"function","name":"git_status","description":"Inspect repository state.","parameters":{"type":"object","properties":{}}},
 {"type":"function","name":"git_diff","description":"Inspect current diff before committing.","parameters":{"type":"object","properties":{}}},
 {"type":"function","name":"git_commit","description":"Commit verified project changes.","parameters":{"type":"object","properties":{"message":{"type":"string"}},"required":["message"]}},
]

FN = {"read_file":read_file,"write_file":write_file,"run_command":run_command,"git_status":git_status,"git_diff":git_diff,"git_commit":git_commit}

def main():
    task = os.environ.get("OPTIMUSAI_TASK", "").strip()
    if not task:
        raise SystemExit("OPTIMUSAI_TASK is required")
    client = OpenAI()
    messages=[{"role":"user","content":task}]
    for _ in range(24):
        r=client.responses.create(model=MODEL, instructions=SYSTEM, input=messages, tools=TOOLS, max_output_tokens=MAX_OUTPUT)
        tool_outputs=[]
        for item in r.output:
            if getattr(item,"type",None) != "function_call":
                continue
            name=item.name
            args=json.loads(item.arguments or "{}")
            try:
                result=FN[name](**args)
                payload={"ok":True,"result":result}
            except Exception as e:
                payload={"ok":False,"error":f"{type(e).__name__}: {e}"}
            tool_outputs.append({"type":"function_call_output","call_id":item.call_id,"output":json.dumps(payload,ensure_ascii=False)})
        if not tool_outputs:
            print(r.output_text)
            return
        messages.extend(tool_outputs)
    raise RuntimeError("agent tool loop exceeded 24 iterations")

if __name__=="__main__":
    main()
