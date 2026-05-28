.PHONY: help dev-backend dev-frontend migrate compose-up compose-down logs build

help:
	@echo "Targets:"
	@echo "  migrate        Run PostgreSQL SQL migrations"
	@echo "  dev-backend    Start FastAPI locally"
	@echo "  dev-frontend   Start Vite locally"
	@echo "  compose-up     Build and start Docker Compose stack"
	@echo "  compose-down   Stop Docker Compose stack"
	@echo "  logs           Follow Docker Compose logs"
	@echo "  build          Build frontend and backend Docker images"

migrate:
	cd backend && python -m app.db.migrate

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

