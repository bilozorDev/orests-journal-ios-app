# Orest's Journal API

FastAPI backend for the Orest's Journal pet health tracking iOS app.

## Stack

- **FastAPI** - Modern async Python web framework
- **Neon PostgreSQL** - Serverless Postgres database
- **Clerk** - Authentication (Organizations = Families)
- **Cloudflare R2** - File storage (S3-compatible)

## Local Development Setup

### 1. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start local services (Postgres + Redis)

```bash
make start
```

This starts Docker containers for:
- **PostgreSQL** (pgvector) on port 5432
- **Redis** on port 6379

### 3. Configure environment

```bash
cp .env.local .env   # Use local database
# Or: cp .env.neon .env  # Use Neon cloud database
```

### 4. Run database migrations

```bash
make migrate
# Or: alembic upgrade head
```

### 5. Start development server

```bash
make run
# Or: uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make start` | Start Postgres + Redis containers |
| `make stop` | Stop containers (keeps data) |
| `make reset-db` | Fast reset - truncate all tables, clear Redis |
| `make nuke-db` | Full reset - destroy volumes, recreate, run migrations |
| `make logs` | View container logs |
| `make migrate` | Run Alembic migrations |
| `make run` | Start FastAPI dev server |
| `make celery` | Start Celery worker |
| `make celery-beat` | Start Celery beat scheduler |

## Database Management

### Quick Reset (keeps schema)
```bash
make reset-db
```
Truncates all tables and clears Redis. Fast, no need to re-run migrations.

### Full Reset (destroys everything)
```bash
make nuke-db
```
Destroys Docker volumes and recreates database from scratch. Use when schema changes.

### Switch Between Local and Cloud Database
```bash
cp .env.local .env   # Local Postgres (Docker)
cp .env.neon .env    # Neon cloud database
```

## TablePlus Connection (Local)

| Field | Value |
|-------|-------|
| Host | `localhost` |
| Port | `5432` |
| User | `postgres` |
| Password | `postgres` |
| Database | `orests_journal` |

## API Documentation

When running in debug mode, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Pets
- `GET /api/v1/pets?org_id=` - List pets
- `POST /api/v1/pets?org_id=` - Create pet
- `GET /api/v1/pets/{id}` - Get pet
- `PATCH /api/v1/pets/{id}` - Update pet
- `DELETE /api/v1/pets/{id}` - Delete pet

### Foods
- `GET /api/v1/foods?org_id=` - List foods
- `POST /api/v1/foods?org_id=` - Create food
- `PATCH /api/v1/foods/{id}` - Update food
- `DELETE /api/v1/foods/{id}` - Delete food

### Feedings
- `POST /api/v1/feedings` - Record feeding
- `GET /api/v1/feedings/pet/{pet_id}` - List feedings
- `GET /api/v1/feedings/pet/{pet_id}/today` - Today's feedings
- `GET /api/v1/feedings/pet/{pet_id}/calorie-goal` - Get calorie goal
- `POST /api/v1/feedings/pet/{pet_id}/calorie-goal` - Set calorie goal

### Medications
- `GET /api/v1/medications?org_id=` - List medications
- `POST /api/v1/medications` - Create medication
- `GET /api/v1/medications/pet/{pet_id}/active` - Active medications

### Doses
- `POST /api/v1/doses` - Record dose
- `GET /api/v1/doses/medication/{id}` - List doses
- `GET /api/v1/doses/medication/{id}/today` - Today's doses
- `GET /api/v1/doses/medication/{id}/last` - Last dose

### Health Events
- `GET /api/v1/health/pet/{pet_id}/categories` - List categories
- `POST /api/v1/health/pet/{pet_id}/events` - Create event
- `GET /api/v1/health/pet/{pet_id}/events` - List events
- `DELETE /api/v1/health/events/{id}` - Delete event

## Deployment (Railway)

1. Connect your GitHub repo to Railway
2. Add environment variables in Railway dashboard
3. Railway will auto-deploy on push

## Authentication

All endpoints require a valid Clerk JWT token in the `Authorization` header:

```
Authorization: Bearer <clerk_jwt_token>
```

The iOS app should use Clerk's SDK to get the token.
