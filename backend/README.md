# Orest's Journal API

FastAPI backend for the Orest's Journal pet health tracking iOS app.

## Stack

- **FastAPI** - Modern async Python web framework
- **Neon PostgreSQL** - Serverless Postgres database
- **Clerk** - Authentication (Organizations = Families)
- **Cloudflare R2** - File storage (S3-compatible)

## Setup

### 1. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required environment variables:
- `DATABASE_URL` - Neon PostgreSQL connection string
- `CLERK_SECRET_KEY` - Clerk API secret key
- `CLERK_JWT_ISSUER` - Clerk JWT issuer URL
- `S3_*` - Cloudflare R2 credentials

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Start development server

```bash
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`

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
