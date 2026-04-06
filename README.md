# LangGraph Email Agent (Local, Privacy-First)

This project is a **fully local** LangGraph-based email assistant with a chat interface.
It combines a FastAPI backend, Ollama models, IMAP email tools, and a web UI.

## Project Overview

The system solves two core needs:

1. Local LLM chat with a tool-using agent flow
2. Operational email automation on your mailbox (listing, summarizing, attachment workflows, draft generation)

Tools are used through LangGraph tool-calling. Conversations are managed by thread and shown as separate sessions in the UI.

## Key Features

- Local, privacy-first workflow (Ollama + local services)
- Multi-conversation sidebar with auto-generated chat titles
- LangGraph + MemorySaver thread-based context handling
- IMAP tools for listing unread emails
- IMAP tools for UID-based email summarization
- IMAP tools for extracting action items and deadline-like patterns
- IMAP tools for listing email attachments
- IMAP tools for exporting email metadata by topic
- IMAP tools for saving attachments by topic
- IMAP tools for drafting emails in a style similar to user history
- Model Settings page for downloading models from catalog
- Model Settings page for deleting installed models
- Model Settings page for switching active model
- Benchmark module for multi-model comparison
- Benchmark module for CSV summaries and Markdown/HTML reports

## Architecture

- `app/main.py`: FastAPI entrypoint, UI routes, and API router registration
- `app/agent/graph.py`: LangGraph workflow (agent -> tools -> agent)
- `app/agent/tool_registry.py`: Agent tool catalog
- `app/agent/tools/email_tools.py`: IMAP-based email tools
- `app/services/ollama_service.py`: Ollama model management and catalog validation
- `app/web/*`: Chat and model settings frontend
- `bench/*`: Benchmark and reporting scripts

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com/) installed and running
- An IMAP-enabled email account (if you want to use email tools)

## Setup

```bash
cd LocalAgentDissertation
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update `.env` with your own values.

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `APP_NAME` | API title | `Step 13 Model Panel API` |
| `PRIVACY_MODE` | Exposed in `/health` | `true` |
| `OLLAMA_BASE_URL` | Ollama base URL | `http://127.0.0.1:11434` |
| `DEFAULT_MODEL` | Default model name | `qwen2.5:7b` |
| `IMAP_HOST` | IMAP server host | empty |
| `IMAP_USER` | IMAP username | empty |
| `IMAP_PASSWORD` | IMAP password/app password | empty |
| `IMAP_FOLDER` | Inbox folder | `INBOX` |
| `IMAP_SENT_FOLDER` | Sent folder (for style analysis) | `Sent` |

## Run

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8013 --env-file .env
```

UI and docs:

- Chat UI: `http://127.0.0.1:8013/`
- Model Settings: `http://127.0.0.1:8013/settings`
- Swagger: `http://127.0.0.1:8013/docs`

## API Endpoints

- `GET /health`
- `GET /tools`
- `POST /chat`
- `GET /models/catalog`
- `GET /models`
- `POST /models/pull` (catalog models only)
- `POST /models/delete`
- `GET /models/active`
- `POST /models/active`

## Example Usage Flow

1. Open `/settings` and download a model from the catalog.
2. Set that model as active.
3. Return to `/` and start a new chat.
4. Ask email-focused prompts, such as: `List the last 5 unread emails`, `Summarize email UID 1234`, `Save attachments for topic: invoice`.

## Benchmark and Reporting

The benchmark script sends test requests to `/chat` for eligible models and collects:

- latency
- success/error rate
- approximate RAM/CPU averages

Run:

```bash
source .venv/bin/activate
python bench/run_benchmark.py
python bench/generate_report.py
```

Generated files:

- `bench/results.csv`
- `bench/summary.csv`
- `bench/report.md`
- `bench/report.html`

## Privacy Notes

This project is local-first, but IMAP tools still process real email data, so:

- never commit `.env`
- use app passwords instead of your primary account password
- review exported data (`email_exports/` style folders) before sharing

## License

There is currently no license file in this repository. If you plan open-source distribution, add an appropriate `LICENSE` file.
