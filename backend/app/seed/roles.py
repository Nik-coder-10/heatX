"""Role seed data for initial role creation."""

from sqlalchemy.orm import Session
from app.models.role import Role
from app.database.enums import UserRole


def seed_roles(db: Session) -> None:
    """Seed default roles into the database.

    This function is idempotent - it will only create roles that don't already exist.

    Args:
        db: Database session
    """
    # Define the default roles to seed
    default_roles = [
        {
            "name": UserRole.ADMIN,
            "description": "Administrator with full system access"
        },
        {
            "name": UserRole.RESEARCHER,
            "description": "Researcher with access to analytical tools and data"
        },
        {
            "name": UserRole.PLANNER,
            "description": "Planner with access to planning and visualization tools"
        },
        {
            "name": UserRole.VIEWER,
            "description": "Viewer with read-only access to reports and data"
        }
    ]

    # Create each role if it doesn't already exist
    for role_data in default_roles:
        # Check if role with this name already exists
        existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing_role:
            # Create new role
            role = Role(
                name=role_data["name"],
                description=role_data["description"]
            )
            db.add(role)

    # Commit all new roles at once
    db.commit()