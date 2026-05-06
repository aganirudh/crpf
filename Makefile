# PRAMAAN — convenience entry points
# All commands work on Windows (PowerShell), macOS, and Linux as long as
# the prerequisites in the README are installed.

.PHONY: help install install-backend install-frontend \
        infra-up infra-down infra-logs infra-reset \
        backend frontend dev \
        db-migrate db-revision db-reset \
        ledger-verify replay test lint format \
        seed clean

# ────────────────────────────────────────────────────────────────────────────
help:
	@echo "PRAMAAN make targets"
	@echo ""
	@echo "  install            install backend + frontend deps"
	@echo "  infra-up           start Postgres / MinIO / Qdrant / OPA"
	@echo "  infra-down         stop infra"
	@echo "  infra-logs         tail infra logs"
	@echo "  infra-reset        wipe infra volumes (destructive)"
	@echo "  db-migrate         apply Alembic migrations"
	@echo "  db-revision m=...  create a new Alembic revision"
	@echo "  db-reset           drop + recreate + migrate (dev only)"
	@echo "  backend            run FastAPI dev server"
	@echo "  frontend           run Next.js dev server"
	@echo "  dev                run backend + frontend together"
	@echo "  seed               seed the demo tender + bidders"
	@echo "  test               run pytest"
	@echo "  lint               ruff check"
	@echo "  format             ruff format"
	@echo "  ledger-verify      verify the audit ledger hash chain"
	@echo "  replay b=<bundle>  replay a signed report bundle"

# ────────────────────────────────────────────────────────────────────────────
install: install-backend install-frontend

install-backend:
	cd backend && uv sync

install-frontend:
	cd frontend && npm install

# ────────────────────────────────────────────────────────────────────────────
infra-up:
	docker compose -f infra/docker-compose.yml up -d
	@echo ""
	@echo "Infra up. Endpoints:"
	@echo "  Postgres   localhost:5432  (pramaan / pramaan)"
	@echo "  MinIO      http://localhost:9001  (pramaan / pramaanpramaan)"
	@echo "  Qdrant     http://localhost:6333"
	@echo "  OPA        http://localhost:8181"

infra-down:
	docker compose -f infra/docker-compose.yml down

infra-logs:
	docker compose -f infra/docker-compose.yml logs -f

infra-reset:
	docker compose -f infra/docker-compose.yml down -v

# ────────────────────────────────────────────────────────────────────────────
db-migrate:
	cd backend && uv run alembic upgrade head

db-revision:
	cd backend && uv run alembic revision --autogenerate -m "$(m)"

db-reset:
	cd backend && uv run python -m pramaan.scripts.db_reset

# ────────────────────────────────────────────────────────────────────────────
backend:
	cd backend && uv run uvicorn pramaan.main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	cd frontend && npm run dev

dev:
	@echo "Run 'make backend' in one terminal and 'make frontend' in another."
	@echo "(A single 'make dev' that runs both is easier with 'concurrently'; install if desired.)"

# ────────────────────────────────────────────────────────────────────────────
seed:
	cd backend && uv run python -m pramaan.scripts.seed_demo

test:
	cd backend && uv run pytest -q

lint:
	cd backend && uv run ruff check .

format:
	cd backend && uv run ruff format .

# ────────────────────────────────────────────────────────────────────────────
ledger-verify:
	cd backend && uv run python -m pramaan.scripts.ledger_verify

replay:
	cd backend && uv run python -m pramaan.scripts.replay --bundle $(b)

clean:
	rm -rf backend/.venv frontend/node_modules frontend/.next
