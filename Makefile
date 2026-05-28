.PHONY: help install-frontend build-frontend backend-check migrate up down logs ps

help:
	@echo "Sustainable AI Demo Interface"
	@echo "  make install-frontend  Install frontend dependencies"
	@echo "  make build-frontend    Build frontend"
	@echo "  make backend-check     Python compile check"
	@echo "  make migrate           Run DB migrations inside backend container"
	@echo "  make up                Start Docker Compose stack"
	@echo "  make down              Stop Docker Compose stack"
	@echo "  make logs              Follow logs"

install-frontend:
	cd frontend && npm install

build-frontend:
	cd frontend && npm run build

backend-check:
	cd backend && python -m compileall -q app

migrate:
	docker compose run --rm backend python -m app.db.migrate

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps
