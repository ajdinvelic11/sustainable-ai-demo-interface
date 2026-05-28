# Sustainable AI Demo Interface

Production-quality demo web interface for a Sustainable AI hackathon presentation. The application provides a professional control room UI for logging in with a JWT / VC-JWT, starting a fixed five-minute multi-site training demo, watching live PostgreSQL-backed training progress, and reviewing final S3 checkpoint results.

The repository is designed to be pushed to GitHub, cloned on an AWS EC2 VM, configured with environment variables, and run with Docker Compose.

## Project Overview

The interface orchestrates your existing Sustainable AI training backend instead of replacing it.

It reuses:

- `ml_ops.edge_training_commands`
- `ml_ops.manual_training_chain_tests` when compatible
- `ml_ops.manual_training_chain_phases` when compatible
- `ml_ops.training_live_metrics`
- `ml_ops.vw_training_live_latest_metrics`
- existing model result or artifact fields if present on command/metric rows

The demo run sequence is fixed:

| Phase | Site | Region | Target | Duration |
| --- | --- | --- | --- | --- |
| 1 | Wiener Neustadt | `region_2` | 20% | 60s |
| 2 | Wien | `region_1` | 30% | 90s |
| 3 | Eisenstadt | `region_3` | 30% | 90s |
| 4 | Wiener Neustadt | `region_2` | 20% | 60s |

Total: 100%, 300 seconds.

## Architecture

- Frontend: React, Vite, TypeScript, Tailwind CSS, lucide-react
- Backend: FastAPI, Pydantic, psycopg 3, httpx, PyJWT
- Database: existing PostgreSQL database `sustainable_ai_weather`
- Artifacts: existing S3 bucket `weather-data-intelligent-ai-training`
- Auth: external VC-JWT compliance validation, then internal short-lived application session JWT in an HttpOnly cookie
- Certificates: signed JSON export for completed Sustainable AI training runs
- Live updates: Server-Sent Events from FastAPI to the browser
- Deployment: backend container, frontend container, Nginx reverse proxy on port `30080`

## Repository Structure

```text
sustainable-ai-demo-interface/
|-- frontend/
|   |-- src/
|   |   |-- components/
|   |   |-- pages/
|   |   |-- api/
|   |   |-- hooks/
|   |   |-- types/
|   |   `-- main.tsx
|   |-- package.json
|   |-- vite.config.ts
|   |-- tailwind.config.ts
|   `-- Dockerfile
|-- backend/
|   |-- app/
|   |   |-- main.py
|   |   |-- config.py
|   |   |-- auth/
|   |   |-- db/
|   |   |-- routes/
|   |   |-- services/
|   |   |-- schemas/
|   |   `-- utils/
|   |-- sql/
|   |   |-- 001_demo_ui_tables.sql
|   |   `-- 002_demo_ui_indexes.sql
|   |-- requirements.txt
|   `-- Dockerfile
|-- deploy/
|   |-- nginx.conf
|   `-- caddy/
|-- docker-compose.yml
|-- .env.example
|-- README.md
`-- Makefile
```

## Prerequisites

- Docker and Docker Compose
- Git
- Network access from EC2 to PostgreSQL/RDS
- Network access from EC2 to the VC-JWT validation endpoint
- Security Group inbound rule for TCP `30080`
- PostgreSQL user with permission to:
  - read `ml_ops` tables/views
  - insert/update `ml_ops.edge_training_commands`
  - create/read/update `ml_ops.demo_ui_runs`
  - create/read `ml_ops.demo_ui_events`

## Environment Variables

Copy `.env.example` to `.env`.

Important variables:

- `APP_PUBLIC_URL`: public URL, for example `http://<EC2_PUBLIC_IP>:30080`
- `APP_JWT_SECRET`: long random secret for internal app sessions
- `APP_ADMIN_SUBJECTS`: comma-separated credential subjects allowed to reset stale state
- `SESSION_COOKIE_NAME`: HttpOnly cookie name
- `CORS_ALLOWED_ORIGINS`: allowed frontend origins
- `VC_JWT_VALIDATION_URL`: external Gaia-X validation endpoint
- `VC_JWT_VALIDATION_MOCK_MODE`: local emergency/demo mode only
- `DB_*`: PostgreSQL settings
- `DEMO_*`: orchestration behavior
- `SITE_*`: configured training sites
- `S3_BUCKET`: checkpoint bucket name
- `CERTIFICATE_SIGNING_SECRET`: long random HMAC secret used to sign exported JSON certificates
- `CERTIFICATE_ISSUER`: issuer name embedded in exported certificates

## Authentication

The login page accepts a JWT / VC-JWT. The backend validates it as follows:

1. Validate basic JWT shape.
2. Decode claims locally only for display/session metadata.
3. If `VC_JWT_VALIDATION_MOCK_MODE=true`, accept the token and show "Demo Auth Mode" in the UI.
4. Otherwise call the external validation API configured via `VC_JWT_VALIDATION_URL`.
5. The external request uses:

```http
POST /api/jwt/compliance-verification
Content-Type: application/vc+jwt

<raw VC-JWT>
```

The Swagger UI for the referenced Gaia-X Basic Functions service documents a `201` response for the compliance verification endpoint. The backend therefore treats 2xx responses as success unless a configured JSON compliant field is present and false.

After successful validation, the backend creates an internal short-lived app session JWT and sets it as an HttpOnly cookie. The raw JWT / VC-JWT is not stored in the browser.

## CSRF Handling

Because the app uses an HttpOnly cookie, mutating API calls use an in-memory CSRF token returned by `/api/auth/me` or `/api/auth/verify`. The frontend sends it as `X-CSRF-Token` for `POST` requests. The token is not stored in localStorage.

## Database Migrations

The app starts even if demo UI tables are missing, but demo endpoints return a clear migration-required response until migrations are applied.

Apply migrations:

```bash
cp .env.example .env
# edit .env first
docker compose build backend
docker compose run --rm backend python -m app.db.migrate
```

The migrations create:

- `ml_ops.demo_ui_runs`
- `ml_ops.demo_ui_events`
- indexes for run status and event history

No historical runs are deleted. No S3 artifacts are deleted.

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

For local auth without the external service:

```env
VC_JWT_VALIDATION_MOCK_MODE=true
```

Use a syntactically valid three-part JWT. If you need admin reset locally, set `APP_ADMIN_SUBJECTS` to the `sub` claim of that token.

## Docker Compose Deployment

```bash
cp .env.example .env
# edit .env
docker compose up --build -d
docker compose logs -f
```

Open:

```text
http://localhost:30080/
```

On EC2:

```text
http://<EC2_PUBLIC_IP>:30080/
```

## AWS EC2 Deployment Steps

1. Launch an EC2 VM, for example Ubuntu 22.04 or 24.04.
2. Open Security Group inbound TCP `30080` from your demo audience IP range.
3. Ensure outbound access to RDS and the VC-JWT validator.
4. Install Docker and Git.
5. Clone this repository.
6. Copy `.env.example` to `.env`.
7. Set `APP_PUBLIC_URL=http://<EC2_PUBLIC_IP>:30080`.
8. Set real DB credentials.
9. Set `APP_JWT_SECRET` to a long random value.
10. Keep `VC_JWT_VALIDATION_MOCK_MODE=false` for production-like demos.
11. Run migrations.
12. Start Docker Compose.

Example:

```bash
git clone <your-repo-url>
cd sustainable-ai-demo-interface
cp .env.example .env
nano .env
docker compose build
docker compose run --rm backend python -m app.db.migrate
docker compose up -d
docker compose logs -f
```

## How To Start The Demo

1. Open the UI.
2. Paste a valid JWT / VC-JWT.
3. Click `Verify & Login`.
4. Click `Start Demo Run`.
5. Watch the live dashboard:
   - Wiener Neustadt 20%
   - Wien 30%
   - Eisenstadt 30%
   - Wiener Neustadt 20%
6. Review the final checkpoint URI and phase table.
7. Click `Export Digital Certificate` to download the signed JSON certificate, or `Export JWT Certificate` to download a signed `.jwt` file.

## Digital Certificate Export

Completed demo runs can be exported as signed JSON certificates from the final results screen or through:

```http
GET /api/demo-runs/{demo_run_id}/certificate
```

The same certificate payload can also be downloaded as an HS256-signed JWT:

```http
GET /api/demo-runs/{demo_run_id}/certificate.jwt
```

The endpoint is protected by the same HttpOnly-cookie session as the demo APIs. It only exports certificates for runs with status `COMPLETED`.

The certificate includes:

- certificate metadata: `certificate_type`, `certificate_version`, `certificate_id`, `issued_at`, `issuer`
- run metadata: `demo_run_id`, `demo_name`, `status`, `started_at`, `finished_at`
- model metadata: `model_id`, `model_version`, `training_type`, `use_case`
- final result: `final_training_run_id`, `final_checkpoint_s3_uri`
- all available phase records from `ml_ops.manual_training_chain_phases`
- command details from `ml_ops.edge_training_commands`
- phase metrics: `map50`, `precision`, `recall`
- integrity fields: `payload_sha256`, `signature_algorithm`, `signature`

Signing uses HMAC-SHA256. The backend first canonicalizes the certificate payload, hashes it into `payload_sha256`, and then signs the canonical signed payload with `CERTIFICATE_SIGNING_SECRET`. The raw signing secret is never exposed to the browser and must not be committed.

The JWT export uses the standard JWT compact serialization with this header:

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

It is signed with the same `CERTIFICATE_SIGNING_SECRET` and is returned as `text/plain` with filename `sustainable-ai-certificate-run-{demo_run_id}.jwt`.

If a phase or final `output_checkpoint_s3_uri` is missing but a `training_run_id` exists, the backend derives the expected URI as:

```text
s3://{S3_BUCKET}/model-checkpoints/{DEMO_MODEL_ID}/{DEMO_MODEL_VERSION}/region_code={region_code}/location_name={location_name_with_underscores}/run_id={training_run_id}/last_checkpoint/last.pt
```

## Reset Stale Runs

Only subjects listed in `APP_ADMIN_SUBJECTS` can reset stale state.

The reset action:

- marks active UI runs as `FAILED`
- optionally marks open edge commands as `FAILED`
- never deletes historical runs
- never deletes S3 artifacts

Use this if commands are stuck in `PENDING`, `PICKED_UP`, or `RUNNING` and you intentionally want to prepare a new demo.

## Backend API

Auth:

- `POST /api/auth/verify`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/auth/config`

Demo:

- `POST /api/demo-runs/start`
- `GET /api/demo-runs/current`
- `GET /api/demo-runs/{demo_run_id}`
- `GET /api/demo-runs/{demo_run_id}/events`
- `GET /api/demo-runs/{demo_run_id}/certificate`
- `GET /api/demo-runs/{demo_run_id}/certificate.jwt`
- `GET /api/demo-runs/stream`
- `POST /api/demo-runs/reset-stale`
- `GET /api/system/sites`
- `GET /health`
- `GET /ready`

## Troubleshooting

### DB connection failed

- Check `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_SSLMODE`.
- Confirm EC2 can reach RDS Security Group.
- Run `docker compose logs backend`.
- Open `/ready` and check `database`.

### Authentication failed

- Check `VC_JWT_VALIDATION_URL`.
- Confirm the token is a VC-JWT and not a JSON wrapper.
- Confirm `VC_JWT_VALIDATION_MOCK_MODE=false` in production.
- For emergency demo mode, set `VC_JWT_VALIDATION_MOCK_MODE=true` and restart containers.

### No live metrics

- Confirm edge agents write to `ml_ops.training_live_metrics`.
- If `ml_ops.vw_training_live_latest_metrics` exists, the app prefers it.
- Check whether rows contain `command_id` or `training_run_id` matching the active command.

### Command stuck in RUNNING

- Inspect `ml_ops.edge_training_commands`.
- Check edge-agent logs on the relevant training site.
- Use admin reset only after confirming the command is stale.

### S3 checkpoint missing

- Confirm the training container uploads to `s3://weather-data-intelligent-ai-training/model-checkpoints/`.
- Confirm the command row or result payload includes a checkpoint URI field.
- The UI looks for common fields such as `output_checkpoint_s3_uri`, `final_checkpoint_s3_uri`, `checkpoint_s3_uri`, and `best_model_s3_uri`.
- Certificate export derives the expected checkpoint URI from `S3_BUCKET`, `DEMO_MODEL_ID`, `DEMO_MODEL_VERSION`, `region_code`, `location_name`, and `training_run_id` when the DB field is missing.

### Certificate export failed

- Confirm the run status is `COMPLETED`.
- Set `CERTIFICATE_SIGNING_SECRET` to a long random value and restart the backend.
- Confirm the demo UI migrations are applied.
- Check backend logs for certificate generation errors.

### Port 30080 not reachable

- Check EC2 Security Group inbound rule.
- Run `docker compose ps`.
- Check reverse proxy logs with `docker compose logs -f reverse-proxy`.

## HTTPS

If you have a domain, use Caddy or Nginx with Let's Encrypt. A sample Caddyfile is included under `deploy/caddy/`.

If you only have an IP address, browser-trusted HTTPS is not possible with Let's Encrypt. For an internal demo, use HTTP on `30080`, or use a self-signed certificate only if your audience can trust it manually.

## Security Notes

- Do not commit `.env`.
- Use a long random `APP_JWT_SECRET`.
- Use a separate long random `CERTIFICATE_SIGNING_SECRET`.
- Keep `VC_JWT_VALIDATION_MOCK_MODE=false` outside local/emergency demo mode.
- Restrict EC2 Security Group ingress.
- Prefer a least-privilege DB user for the UI.
- Use HTTPS with a domain for production.
- Raw JWT / VC-JWT tokens are not stored by the frontend.
- S3 artifacts are never deleted by this app.
