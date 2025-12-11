.PHONY: start stop reset-db nuke-db logs migrate run celery celery-beat

# Python from venv
PYTHON = venv/bin/python
PIP = venv/bin/pip

# Start Postgres + Redis containers
start:
	docker compose up -d

# Stop containers (keeps data)
stop:
	docker compose down

# Fast reset - truncate all tables, clear Redis
reset-db:
	$(PYTHON) scripts/reset_db.py

# Full reset - destroy volumes, recreate, run migrations
nuke-db:
	docker compose down -v
	docker compose up -d
	@echo "Waiting for Postgres to start..."
	@sleep 3
	$(PYTHON) -m alembic upgrade head

# View container logs
logs:
	docker compose logs -f

# Run database migrations
migrate:
	$(PYTHON) -m alembic upgrade head

# Run FastAPI dev server
run:
	$(PYTHON) -m uvicorn app.main:app --reload

# Run Celery worker
celery:
	$(PYTHON) -m celery -A app.core.celery_app worker --loglevel=info

# Run Celery beat scheduler
celery-beat:
	$(PYTHON) -m celery -A app.core.celery_app beat --loglevel=info
