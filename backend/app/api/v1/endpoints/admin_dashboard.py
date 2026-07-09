"""Admin dashboard endpoints — stats, user counts, system overview."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import get_current_user
from app.core.database import get_db
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.audit_repository import AuditLogRepository

router = APIRouter()


@router.get("/")
def get_admin_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_repo = UserRepository(db)
    role_repo = RoleRepository(db)
    audit_repo = AuditLogRepository(db)

    total_users = user_repo.count_active()
    verified_users = user_repo.count_verified()
    total_roles = len(role_repo.get_all_roles())
    login_events = audit_repo.count_by_action("user.login")

    return {
        "total_users": total_users,
        "verified_users": verified_users,
        "total_roles": total_roles,
        "successful_logins": login_events,
    }
