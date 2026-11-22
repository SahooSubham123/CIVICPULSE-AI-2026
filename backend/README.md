# CIVICPULSE AI backend

FastAPI REST API for the CIVICPULSE AI frontend. Routes are versioned under `/api/v1`; interactive OpenAPI documentation is available at `/docs`.

## Run locally

Requirements: Python 3.11+ and PostgreSQL 14+ (a local SQLite file is used only when `DATABASE_URL` is unset).

From the repository root in PowerShell:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `DATABASE_URL` and a unique `JWT_SECRET_KEY`. AI provider keys are optional for startup and required for AI features, including policy PDF ingestion and questions. `DATABASE_URL` accepts a SQLAlchemy URL such as:

```text
postgresql+psycopg://civicpulse_api:<password>@<host>:5432/postgres?sslmode=require
```

For Supabase, use the PostgreSQL connection string from the project database settings and URL-encode special characters in the password. Never commit `.env` or expose provider/database credentials to the browser.

Apply the schema and row-level policies to the project database:

```powershell
alembic upgrade head
```

Set `MIGRATION_DATABASE_URL` to a privileged database connection for running Alembic; if omitted, Alembic uses `DATABASE_URL`. Keep this migration credential server-side and out of the frontend. The migration creates a non-login `civicpulse_app` role and grants it only the table operations needed by the API. The migration runner also receives membership so it can assume that role. Create a separate login role in the Supabase SQL editor, grant it membership, then use that role in the backend-only `DATABASE_URL`:

```sql
CREATE ROLE civicpulse_api LOGIN PASSWORD '<generate-a-unique-secret>';
GRANT civicpulse_app TO civicpulse_api;
```

Use the API login for the service, not `postgres`, `service_role`, or a Supabase `anon` key. The application sets `ROLE civicpulse_app` on each PostgreSQL connection. Request-specific transaction-local settings power RLS, and are reset by PostgreSQL when the transaction ends. The application role is deliberately not a table owner and has `NOBYPASSRLS`. Rotate both role passwords through Supabase and update the backend secret store; never put them in React/Vite variables.

The migration revokes table grants from Supabase's `anon`, `authenticated`, and `service_role` roles when present. Do not configure Supabase browser clients to access these application tables directly.

The PostgreSQL API connection requires TLS by default (`DATABASE_SSL_MODE=require`). Use `disable` only for local, non-production PostgreSQL. `DATABASE_CONNECT_TIMEOUT_SECONDS`, `DATABASE_POOL_SIZE`, and `DATABASE_MAX_OVERFLOW` tune connection behavior.

Start the API:

```powershell
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`. Health check `http://127.0.0.1:8000/health` performs `SELECT 1` and reports a generic 503 if PostgreSQL is unavailable. Run tests with `pytest`.

To run the opt-in PostgreSQL connectivity and rolled-back CRUD checks against a dedicated migrated test project:

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://civicpulse_api:<password>@<host>:5432/postgres?sslmode=require"
pytest tests/integration/test_postgres.py
```

The integration tests check connectivity, CRUD/relationships, pgvector cosine-distance queries, and published-chunk RLS visibility using rows inside rolled-back transactions. Do not point them at a production database. Without `TEST_DATABASE_URL`, these integration checks are skipped.

## Configuration

`backend/.env.example` lists supported variables. To create an initial administrator account, set both `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` before starting the API. If both are empty, public registration creates citizen accounts only. Administrators can also promote accounts through the role-management API. Use a long, unique `JWT_SECRET_KEY`; production startup rejects the development secret and SQLite.

The development app creates tables from SQLAlchemy metadata on startup (`AUTO_CREATE_SCHEMA=true`) only for local SQLite. For any PostgreSQL database, set `AUTO_CREATE_SCHEMA=false`, apply the Alembic migration, then start the app. PostgreSQL startup rejects automatic schema creation; production configuration also requires it to be disabled.

For PostgreSQL local development, also apply the migration before starting because the API connection assumes the `civicpulse_app` role. If your local PostgreSQL server does not support TLS, set `DATABASE_SSL_MODE=disable` only in that local environment.

## API modules

| Module | Endpoints | Access |
|---|---|---|
| Authentication | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` | Registration/login public; profile authenticated |
| User management | `GET/PATCH /users/me`, `GET /users`, `PATCH /users/{id}/role` | Profile authenticated; directory and roles admin |
| Government schemes | `GET/POST /schemes`, `GET/DELETE /schemes/{id}` | Read public; create/archive admin |
| Government documents | `GET/POST /documents`, `GET /documents/{id}` | Read published documents public; ingest admin |
| Policy explainer | `POST /policy/documents/upload`, `GET /policy/documents`, `PATCH /policy/documents/{id}/publication`, `POST /policy/ask` | Upload/publish admin; citizens see published documents, admins also see drafts; asking authenticated |
| AI chatbot | `POST /chat/messages` | Authenticated; configured AI provider required |
| Eligibility | `POST /eligibility/check` | Authenticated; deterministic match against stored criteria |
| Grievances | `POST/GET /grievances`, `POST /grievances/submit`, `GET/PATCH /grievances/{id}`, `GET /grievances/{id}/evidence` | Citizens submit and access own reports; admin reviews, sets final priority/category, and updates status |
| Complaint tracking | `GET /tracking/{reference_number}` | Public reference-only view; does not expose reporter identity |
| Government service assistance | `POST /services/automation/assist`, `GET /services/automation/plans`, `GET /services/automation/portals`, `POST /services/automation/portals/{portal_id}/inspect` | Authenticated; AI guidance, private ephemeral draft fields, read-only Playwright inspection of configured portals |
| Fact verification | `POST /verification/claims`, `GET /verification`, `GET /verification/{id}` | Authenticated; claim reports compare only evidence fetched from configured trusted domains |
| Media analysis | `POST /media-analysis/images`, `POST /media-analysis/audio`, `POST /media-analysis/videos` | Authenticated; bounded image/audio/video uploads and configured AI provider required |
| Admin dashboard | `GET /admin/overview`, `GET /admin/grievances` | Admin; grievance list supports status, priority, and review-status filters |

Protected endpoints require `Authorization: Bearer <access_token>`. Login uses OAuth2 form fields `username` (email) and `password`. Errors use the common `{ "error": { "code", "message", "details" } }` envelope.

## Current boundaries

- AI responses and eligibility matches are advisory and are not official decisions. AI routes return a clear service error when their provider is unconfigured or unavailable.
- Grievance submissions accept optional JPEG, PNG, or WebP evidence (up to `MAX_MEDIA_SIZE_BYTES`) and optional latitude/longitude coordinates. Evidence bytes are stored in PostgreSQL and can be retrieved only by the complaint owner or an administrator. Keep the database encrypted and access-restricted; delete evidence according to the organization's retention policy.
- Grievance AI triage suggests a category and urgency from the report text, but does not assign a case, determine final priority, or make an outcome decision. Each report starts with `review_status=pending` and `status=received`; only an administrator can save final classification/priority or case status and mark the report reviewed. If the AI provider is unavailable or returns invalid data, the complaint is still saved with `ai_triage_status=unavailable` for staff review.
- Policy explainer accepts searchable PDF uploads up to the configured size, page, and extracted-text limits. It extracts page-aware chunks, requests 768-dimensional embeddings, and stores them in PostgreSQL with pgvector. Only published policy documents are eligible for retrieval. Answers are restricted to retrieved excerpts, include document/page citations, and abstain when no sufficiently similar source is found or the model omits valid citations. The PDF bytes are processed in memory and are not retained; the extracted text and chunks remain in the database. Scanned PDFs require OCR before upload.
- Use `AI_PROVIDER=openai` with `OPENAI_API_KEY` and `OPENAI_EMBEDDING_MODEL`, or `AI_PROVIDER=gemini` with `GEMINI_API_KEY` and `GEMINI_EMBEDDING_MODEL`. Embedding vectors are fixed at 768 dimensions to match the migration and index. `POLICY_PDF_MAX_SIZE_BYTES`, `POLICY_PDF_MAX_PAGES`, `POLICY_PDF_MAX_EXTRACTED_CHARS`, `POLICY_CHUNK_SIZE_CHARS`, `POLICY_CHUNK_OVERLAP_CHARS`, `POLICY_MIN_SIMILARITY`, and `POLICY_RETRIEVAL_LIMIT` control ingestion and retrieval limits.
- Fact reports fetch only credential-free HTTPS URLs on domains explicitly configured in `TRUSTED_FACT_SOURCE_DOMAINS` (a JSON list of hostnames); URLs with query strings or fragments are rejected, redirects are not followed, and source responses are bounded. With no readable trusted evidence, claim assessments remain inconclusive and the AI provider is not asked for a verdict. Provider-generated citations are discarded; report sources link only to pages the API fetched. Configure only domains operators have reviewed.
- Fact and media review do not prove truth, falsity, or authenticity. AI confidence is uncalibrated. Image, audio, and video bytes are size/type checked and sent to the configured AI provider, but original media bytes are not retained. Audio and video are limited to ten minutes; video review samples at most six frames and does not analyze its audio track. Audio reports retain the machine-generated transcript and all reports retain evidence excerpts/observations and limitations in PostgreSQL. Transcription and visual observations can be wrong or incomplete; important conclusions require human review. Never label media fake based only on an AI detection score. Tell users that uploads are sent to the configured provider and that audio transcripts remain in their private reports.
- Government-service assistance uses the configured AI provider to suggest procedures, documents, form fields, and tracking guidance. These are unverified suggestions, not legal or eligibility determinations. Citizens' draft field values exist only in frontend memory and are not sent back to or stored by the backend; assistance plans store only a service name and procedure.
- Playwright inspection is public-page, HTTPS-only, and restricted to exact origins in the server-side `GOVERNMENT_SERVICE_PORTALS` JSON setting. Configure only government portals approved by your operators, for example `{"state_services":"https://portal.example.gov/"}`. The inspector uses a fresh in-memory browser context, disables JavaScript, blocks non-GET and active API requests, downloads, and cross-origin requests/redirects, and stores no cookies or browser state. Install the browser runtime after dependencies with `python -m playwright install chromium`.
- Portal passwords, PINs, and one-time codes must never be collected or stored. The assistant does not sign in, fill government forms, submit applications, or make legal declarations; the execute endpoint remains disabled. Citizens must review all data and declarations and submit directly on the official portal themselves. Portal inspection may be unavailable when the Playwright browser is not installed or a portal blocks automated access.
- Government documents and schemes are not preloaded. Admins upload and review policy PDFs before publication; only published policy chunks are searchable. Existing manually created government-document records remain available through the documents API but are not RAG sources unless ingested as a PDF.
- Production migrations enable RLS on user, grievance, service-task, verification, and policy-chunk records; signed-in users can read published policy documents/chunks, admins can also read drafts, and policy writes require admin context. Complaint tracking has a separate exact-reference read policy and a response schema that omits reporter identity. The RLS context depends on the trusted backend service; direct database access must remain restricted to backend operators.
- RLS custom settings are transaction-local, and API sessions set the restricted PostgreSQL role per connection. Never use a database owner, superuser, `BYPASSRLS` role, Supabase service-role key, or public/anon credential as the application's database login. RLS is defense in depth for the trusted backend; never grant untrusted clients the backend database credential or ability to set backend transaction context.
- For production, keep `AUTO_CREATE_SCHEMA=false`, use a secret manager for database credentials, run migrations as a separate privileged deployment step, and verify network allowlists/backups/monitoring before release.
