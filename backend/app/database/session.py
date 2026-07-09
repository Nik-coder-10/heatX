from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create SQLAlchemy engine
engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    pool_pre_ping=True,  # Enable connection health checks
    pool_size=20,
    max_overflow=10,
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()