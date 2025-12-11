from fastapi import APIRouter

from app.api.endpoints import pets, foods, feedings, medications, doses, health, auth, families, dashboard, notifications, uploads

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(families.router, prefix="/families", tags=["families"])
api_router.include_router(pets.router, prefix="/pets", tags=["pets"])
api_router.include_router(foods.router, prefix="/foods", tags=["foods"])
api_router.include_router(feedings.router, prefix="/feedings", tags=["feedings"])
api_router.include_router(medications.router, prefix="/medications", tags=["medications"])
api_router.include_router(doses.router, prefix="/doses", tags=["doses"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
