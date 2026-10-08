# OptimusAI in-project LLM

The LLM runs through the OpenAI API while the Agent executes tools locally in Termux.

Required environment variables:

- OPENAI_API_KEY
- OPTIMUSAI_TASK
- OPTIMUSAI_ROOT (optional)
- OPTIMUSAI_LLM_MODEL (optional; default: gpt-6-luna)

The API key is never stored in Git.

Architecture:

ChatGPT Project Manager
-> Termux Project Manager Agent
-> OpenAI Responses API
-> local tools
-> verification/evidence

The Responses API is used for new integrations; the legacy Assistants API was sunset on August 26, 2026.
