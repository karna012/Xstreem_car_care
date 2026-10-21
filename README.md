# Xstreem Car Care

**Full-stack Python application · FastAPI · SQL / SQLite · JavaScript · Ollama**

A car-care business application connecting a customer website with bookings,
customer and vehicle records, services, memberships and payment tracking.
The admin workspace and a local AI chatbot share the same Python backend.

[API and routes](main.py) · [SQL implementation](database.py) · [AI client](ai_service.py) · [Portfolio walkthrough](https://github.com/karna012/karna012/blob/main/projects/xstreem-car-care.md)

## Application areas

| Area | Included functionality |
| --- | --- |
| Customer website | Service information, booking and membership forms |
| Admin workspace | Customer, vehicle, service, booking and payment-record management |
| Customer history | Token-based history links and QR-code generation |
| AI chat | Business-context responses using a locally hosted Ollama model |
| Messaging | WhatsApp sender and webhook integration requiring provider configuration |

Payment records are administrative tracking; they are not a claim that a payment
gateway has verified a transaction.

## Architecture

```text
Browser: HTML / CSS / JavaScript
                ↓
      FastAPI + Jinja2 templates
         ├── database.py → SQLite
         ├── ai_service.py → local Ollama over HTTP
         └── whatsapp_service.py → messaging provider
```

The implemented backend is **FastAPI**, not Flask. Storage uses Python's
`sqlite3` module and `xtreem.db`; Microsoft SQL Server is not required by this
version.

## Code entry points

- [main.py](main.py): Pydantic request models, API routes, admin dependencies,
  page rendering, QR endpoints and webhook handlers.
- [database.py](database.py): relational schema, migration helpers, joins and
  CRUD operations for the business records.
- [ai_service.py](ai_service.py): reusable asynchronous HTTP client, model
  configuration, timeouts and business-context prompt construction.
- [templates](templates) and [static](static): frontend views and assets.
- [business_info.txt](business_info.txt): business context used by the chatbot.

## Local setup

Use a fresh checkout and disposable development records. Python 3.10+ is required
by the source syntax; use a version compatible with the pinned dependencies.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt jinja2 python-multipart
$env:ADMIN_USERNAME = "local-admin"
$env:ADMIN_PASSWORD = "replace-with-a-unique-local-password"
$env:QR_SECRET = "replace-with-a-separate-random-local-secret"
$env:PUBLIC_BASE_URL = "http://127.0.0.1:8000"
uvicorn main:app --host 127.0.0.1 --port 8000
```

Jinja2 and python-multipart are explicitly included above because the application
uses templates and form/file handling, but the current requirements file does
not list both. The application loads `.env` through python-dotenv; keep any real
values private.

Open `http://127.0.0.1:8000/` for the website and `/admin` for the administrative
interface. Startup initializes/migrates the local SQLite database, so do not
point a development checkout at production records. `clear_db.py` is a data
reset utility, not a routine startup step.

### Optional local AI setup

Install and run Ollama, then obtain the model configured in `OLLAMA_MODEL`.
The source default is `llama3.2:3b`:

```sh
ollama pull llama3.2:3b
```

`OLLAMA_HOST` defaults to `http://127.0.0.1:11434`. The AI client also supports
`OLLAMA_TIMEOUT`, `OLLAMA_KEEPALIVE`, `OLLAMA_NUM_CTX` and
`OLLAMA_NUM_PREDICT`. AI responses require the local service and model to be
available; they are not an offline capability of the website alone.

### Optional messaging setup

The WhatsApp integration reads `WHATSAPP_PHONE_NUMBER_ID`,
`WHATSAPP_ACCESS_TOKEN` and `VERIFY_TOKEN` from the environment. Configure your
own provider account and review webhook protection before enabling public
traffic. Never commit tokens or copy production messaging credentials into
examples.

## Development status

This repository demonstrates a full-stack business workflow. It is **not a
security-hardened release** or a claim of production readiness. Before using
real customer records, review authorization on every route, replace development
defaults, protect private uploads and customer-history links, verify incoming
webhooks, and use HTTPS.

There is no dedicated automated test suite in the current repository. API tests,
dependency cleanup and security hardening are useful next steps. Setup commands
above reflect the current code; they are not evidence of a full deployment test.

Live databases, private keys and environment secrets do not belong in the
repository. Review `.gitignore` and staged files before every push.

## License

This project is licensed under the MIT License.

---

Built by [Karan Ramesh](https://github.com/karna012).
