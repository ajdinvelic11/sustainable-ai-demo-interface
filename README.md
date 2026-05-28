# Sustainable AI Demo Interface

Production-ready demo web interface for the Sustainable AI multi-site training workflow. The app lets a presenter log in with a JWT / VC-JWT token, start a fixed 5-minute training chain, monitor live PostgreSQL metrics, and view final S3 checkpoint results.

## Architecture

- **Frontend:** React, Vite, TypeScript, Tailwind CSS, lucide-react, Recharts.
- **Backend:** FastAPI, Pydantic, psycopg, Server-Sent Events.
- **Database:** Reuses `ml_ops.edge_training_commands`, `ml_ops.manual_training_chain_tests`, `ml_ops.manual_training_chain_phases`, `ml_ops.training_live_metrics`, and `ml_ops.vw_training_live_latest_metrics` when available.
- **Demo tables:** Adds `ml_ops.demo_ui_runs` and `ml_ops.demo_ui_events` for UI state and event history.
- **Deployment:** Docker Compose with backend, frontend, and Nginx reverse proxy exposed on `30080`.

The backend does not redesign the existing training system. It writes compatible pending commands to PostgreSQL and reads command status, live metrics, and checkpoint output from PostgreSQL.

## Demo Flow

1. Open `http://<EC2_PUBLIC_IP>:30080/`.
2. Paste a JWT / VC-JWT token and log in.
3. Click **Start Demo Run**.
4. Watch the phase sequence:
   - Phase 1: Wiener Neustadt, `region_2`, 20%, 60 seconds
   - Phase 2: Wien, `region_1`, 30%, 90 seconds
   - Phase 3: Eisenstadt, `region_3`, 30%, 90 seconds
   - Phase 4: Wiener Neustadt, `region_2`, 20%, 60 seconds
5. View final metrics and the final checkpoint S3 URI.

## Prerequisites

- Docker and Docker Compose on the deployment VM.
- Network access from the VM to PostgreSQL.
- Existing Sustainable AI edge agents polling `ml_ops.edge_training_commands`.
- PostgreSQL credentials supplied through `.env`.
- VC-JWT validation endpoint configured, or explicit mock mode for local/demo fallback.

## Local Development

Copy the environment file:

```bash
cp .env.example .env
```

Install backend dependencies:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install frontend dependencies:

```bash
cd frontend
npm install
```

Run migrations:

```bash
cd backend
python -m app.db.migrate
```

Start the backend:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Start the frontend:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173/`.

## Environment Variables

- `APP_ENV`: Use `production` on EC2.
- `APP_PUBLIC_URL`: Public URL, for example `http://<EC2_PUBLIC_IP>:30080`.
- `APP_JWT_SECRET`: Required. Change this before production.
- `APP_ADMIN_SUBJECTS`: Comma-separated subjects allowed to reset stale runs.
- `SESSION_COOKIE_NAME`: HttpOnly cookie name for the app session.
- `CORS_ALLOWED_ORIGINS`: Comma-separated frontend origins.
- `VC_JWT_VALIDATION_ENABLED`: Enables external VC-JWT validation.
- `VC_JWT_VALIDATION_MOCK_MODE`: Accepts tokens without external validation when `true`. The UI displays **Demo Auth Mode**.
- `VC_JWT_VALIDATION_URL`: Default documented endpoint is `https://gxdch-nas-basic-functions.cloudcarib.com/api/jwt/compliance-verification`.
- `VC_JWT_VALIDATION_CONTENT_TYPE`: Default is `application/vc+jwt`.
- `VC_JWT_VALIDATION_EXPECTED_COMPLIANT_FIELD`: If the response JSON includes this field, it must be true.
- `DB_*`: PostgreSQL connection settings.
- `DEMO_*`: Model ID, version, timing, polling, and edge command type.
- `SITE_*`: Site names and region codes.
- `S3_BUCKET`: Artifact bucket name.

## Database Migrations

Run:

```bash
docker compose run --rm backend python -m app.db.migrate
```

The migrations create:

- `ml_ops.demo_ui_runs`
- `ml_ops.demo_ui_events`
- indexes for status, created time, and event lookup

If these tables are missing, the app still starts and `/health` works, but starting a demo returns a setup warning until migrations are applied.

## AWS EC2 Deployment

1. Launch an EC2 instance with Docker installed.
2. Allow inbound TCP `30080` from your demo audience IP range in the Security Group.
3. Clone the repository:

```bash
git clone <your-repo-url>
cd sustainable-ai-demo-interface
```

4. Create `.env`:

```bash
cp .env.example .env
nano .env
```

5. Set real values for `APP_PUBLIC_URL`, `APP_JWT_SECRET`, `DB_PASSWORD`, and VC-JWT validation.
6. Run migrations:

```bash
docker compose run --rm backend python -m app.db.migrate
```

7. Start the stack:

```bash
docker compose up -d --build
```

8. Follow logs:

```bash
docker compose logs -f
```

Open `http://<EC2_PUBLIC_IP>:30080/`.

## Docker Compose

Services:

- `backend`: FastAPI on internal port `8000`.
- `frontend`: Built React static assets served by Nginx on internal port `80`.
- `reverse-proxy`: Nginx exposed as host port `30080`.

Useful commands:

```bash
docker compose ps
docker compose logs -f backend
docker compose restart backend
docker compose down
```

## Authentication

The login page accepts a pasted JWT / VC-JWT token. The backend posts the raw token to the configured validation endpoint using `Content-Type: application/vc+jwt`. The public Swagger metadata identifies the compliance endpoint as:

```text
POST /api/jwt/compliance-verification
operationId: JWTController_verifyComplianceVc
```

When validation succeeds, the backend creates a short-lived internal app JWT and stores it in a secure HttpOnly cookie. Demo API endpoints require this app session. Logout clears the cookie.

Cookie auth uses `SameSite=Lax`, HttpOnly cookies, JSON-only state-changing endpoints, and explicit confirmation for stale reset. For internet-facing production, use HTTPS with a domain and restrict origins.

## Mock Auth Mode

Set:

```env
VC_JWT_VALIDATION_MOCK_MODE=true
```

The backend logs this clearly and the UI displays **Demo Auth Mode**. Do not use mock mode for production.

## Resetting Stale Runs

Only admins can reset stale demo state. Configure admins with:

```env
APP_ADMIN_SUBJECTS=subject-1,subject-2
```

Reset marks active demo UI runs as `FAILED`. The confirmation flow can also mark open edge commands with `PENDING`, `PICKED_UP`, or `RUNNING` as `FAILED`. Historical runs and S3 artifacts are never deleted.

## VC-JWT Configuration

Default adapter behavior:

- Method: `POST`
- Body: raw token string
- Content-Type: `application/vc+jwt`
- Success: any 2xx response is accepted unless the configured compliance field is present and false.

If the external API changes, update:

```env
VC_JWT_VALIDATION_URL=
VC_JWT_VALIDATION_CONTENT_TYPE=
VC_JWT_VALIDATION_EXPECTED_COMPLIANT_FIELD=
```

## Troubleshooting

**DB connection failed**

- Check `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, and `DB_SSLMODE`.
- Confirm the EC2 Security Group can reach the RDS Security Group.
- Run `docker compose logs -f backend`.

**Authentication failed**

- Confirm `VC_JWT_VALIDATION_URL` is reachable from the VM.
- Confirm token type matches `VC_JWT_VALIDATION_CONTENT_TYPE`.
- For emergency demo fallback, set `VC_JWT_VALIDATION_MOCK_MODE=true` and redeploy.

**No live metrics**

- Confirm `ml_ops.vw_training_live_latest_metrics` or `ml_ops.training_live_metrics` exists.
- Check that edge agents write `command_id`, `training_run_id`, progress, and metric columns.

**Command stuck in RUNNING**

- Inspect `ml_ops.edge_training_commands` for the current `command_id`.
- Check the target edge agent logs.
- Use admin reset only after confirming the command is stale.

**S3 checkpoint missing**

- Confirm the training container uploaded to `s3://weather-data-intelligent-ai-training/model-checkpoints/`.
- Confirm the command row or result table records `output_checkpoint_s3_uri`, `final_checkpoint_s3_uri`, or `best_model_s3_uri`.

**Port 30080 not reachable**

- Check `docker compose ps`.
- Confirm EC2 inbound Security Group rule for TCP `30080`.
- Confirm the host firewall allows the port.

## HTTPS

If you have a domain, point DNS to the EC2 public IP and use Caddy or Nginx with Let's Encrypt. A starter Caddyfile is in `deploy/caddy/Caddyfile`.

If you only have an IP address, browser-trusted HTTPS is not available without a domain. Use HTTP for an internal demo or a self-signed certificate only when your audience can accept the browser warning.

## Security Notes

- Never commit `.env`.
- Change `APP_JWT_SECRET` before production.
- Keep `VC_JWT_VALIDATION_MOCK_MODE=false` in production.
- Use a least-privilege PostgreSQL user. If possible, grant only the required `ml_ops` read/write permissions.
- Restrict the EC2 Security Group to known source IPs.
- Use HTTPS with a domain for production or public demos.

## Known Compatibility Behavior

The existing scripts named in the project brief were not present in this workspace, so the backend uses defensive PostgreSQL schema introspection. It inserts only columns that exist in each target table and stores the command details in `command_payload`, `payload`, `metadata`, or `command_metadata` when those columns exist.

If your edge agent expects a different `command_type`, set:

```env
DEMO_EDGE_COMMAND_TYPE=<expected-value>
```

