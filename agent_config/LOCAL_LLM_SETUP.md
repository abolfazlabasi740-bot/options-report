# OptimusAI Local LLM

The Agent uses a local OpenAI-compatible endpoint and does not require a cloud API.

Recommended runtime:
- llama.cpp
- Termux on Android
- local endpoint: http://127.0.0.1:8080/v1
- no VPN
- no API billing

The official llama.cpp documentation confirms Termux/Android support and an OpenAI-compatible server.

## Runtime contract

Start the local server with a GGUF model:

    llama-server -m ~/models/<MODEL>.gguf --host 127.0.0.1 --port 8080

The Agent then uses:

    OPTIMUSAI_PROVIDER=local
    OPTIMUSAI_API_BASE=http://127.0.0.1:8080/v1
    OPTIMUSAI_API_KEY=local
    OPTIMUSAI_LLM_MODEL=<server-model-name>

Do not expose the server beyond localhost.

## Model selection

Model size must be selected after checking the phone's available RAM and CPU/GPU capabilities. Do not download a large model blindly.

For the first smoke test, prefer a small instruct/coder GGUF (roughly 1B–4B parameters, quantized) and increase only after stability is demonstrated.

## Verification

The first runtime check must verify:
1. llama-server exists and starts.
2. localhost /v1/models responds.
3. the Agent can complete one tool-calling task.
4. Python compilation passes.
5. Git status/diff are captured as evidence.

No production signal is authorized by this setup alone.
