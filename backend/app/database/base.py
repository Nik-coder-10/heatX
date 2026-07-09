from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Define naming conventions for constraints and indexes
# This helps with consistent naming across different database backends
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

# Create metadata with naming conventions
metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """
    Base class for all database models.

    Includes:
    - SQLAlchemy 2.0 DeclarativeBase
    - Consistent naming conventions for constraints and indexes
    - Metadata configuration
    """
    metadata = metadata

    def __repr__(self):
        # Basic string representation showing primary key
        try:
            pk = ", ".join(f"{k}={getattr(self, k)!r}" for k in self.__mapper__.primary_key)
            return f"<{self.__class__.__name__}({pk})>"
        except Exception:
            return f"<{self.__class__.__name__}>"