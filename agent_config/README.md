# OptimusAI in-project LLM

The project uses a **local LLM inside Termux**. There is no cloud model API, no API billing, and no VPN dependency for the Agent runtime.

## Architecture

ChatGPT Project Manager
-> OptimusAI in-project Agent
-> local llama.cpp server
-> GGUF model
-> local filesystem / Python / Git / TSETMC
-> verification and evidence

Runtime endpoint:

    http://127.0.0.1:8080/v1

The server is localhost-only and must not be exposed externally.

## Model

The first production-capable runtime target is:

    Qwen/Qwen3-4B-GGUF:Q4_K_M

The Qwen model card identifies Qwen3-4B as a 4B-parameter model, lists Q4_K_M at about 2.5 GB, and documents llama.cpp plus agent/tool capabilities. citeturn0search0turn0search5

## One-time bootstrap

From Termux:

    cd ~/OptimusAI_V41_LIVE
    bash scripts/setup_local_llm.sh

The script installs build prerequisites, builds llama.cpp, starts the local server, waits for /v1/models, and compiles the Agent entrypoints.

Android/Termux execution of llama.cpp does not require root; the Android build documentation describes Termux installation and CMake compilation. citeturn0search4

## Agent environment

    export OPTIMUSAI_PROVIDER=local
    export OPTIMUSAI_API_BASE=http://127.0.0.1:8080/v1
    export OPTIMUSAI_API_KEY=local
    export OPTIMUSAI_LLM_MODEL='Qwen/Qwen3-4B-GGUF:Q4_K_M'

The `openai` Python package is used only as an OpenAI-compatible client library against localhost. It does not send the Agent traffic to OpenAI.

## Operating rules

- ChatGPT remains Project Manager.
- The in-project Agent performs controlled execution.
- TSETMC is the Single Source of Truth for market data.
- Never invent or impute missing market data.
- Outside TSETMC live hours, use the latest valid snapshot.
- Do not mix old and canonical scoring models.
- Evidence is required before any production trading signal.
- Destructive shell/Git operations remain blocked.

## Verification gate

Setup is not considered complete until:

1. llama-server is running on 127.0.0.1:8080.
2. /v1/models responds.
3. Agent tool-calling completes successfully.
4. Python compilation passes.
5. Git status/diff evidence is captured.
6. A real project task is executed and its result is verified.

No production buy/sell authorization is granted by installation alone.
