from fastapi import APIRouter

from app.api.v1.endpoints import auth, user, role, project, satellite_image, satellite_acquisition, gis, heat_detection, ml_training, inference, recommendation, scenario, report, notification, admin_dashboard, health

api_router = APIRouter()

# Include all routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(user.router, prefix="/users", tags=["users"])
api_router.include_router(project.router, prefix="/projects", tags=["projects"])
api_router.include_router(satellite_image.router, prefix="/satellite", tags=["satellite"])
api_router.include_router(satellite_acquisition.router, prefix="/satellite/acquisition", tags=["satellite-acquisition"])
api_router.include_router(gis.router, prefix="/gis", tags=["gis"])
api_router.include_router(heat_detection.router, prefix="/heat", tags=["heat"])
api_router.include_router(ml_training.router, prefix="/ml/training", tags=["ml-training"])
api_router.include_router(inference.router, prefix="/ml/inference", tags=["ml-inference"])
api_router.include_router(recommendation.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(report.router, prefix="/reports", tags=["reports"])
api_router.include_router(notification.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(role.router, prefix="/roles", tags=["roles"])
api_router.include_router(scenario.router, prefix="/scenarios", tags=["scenarios"])
api_router.include_router(admin_dashboard.router, prefix="/admin", tags=["admin"])
api_router.include_router(health.router, prefix="", tags=["health"])