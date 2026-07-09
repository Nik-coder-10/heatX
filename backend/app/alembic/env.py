from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
import os
import sys

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with application settings
from app.core.config import settings
config.set_main_option("sqlalchemy.url", str(settings.SQLALCHEMY_DATABASE_URI))

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from app.core.database import Base
# Import models to ensure they are registered with Base
from app.models import AuditLog, Role, User, UserRole  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.city import City  # noqa: F401
from app.models.heat_island import HeatIsland  # noqa: F401
from app.models.lst import LSTRecord  # noqa: F401
from app.models.ndbi import NDBIRecord  # noqa: F401
from app.models.ndvi import NDVIRecord  # noqa: F401
from app.models.prediction import Prediction  # noqa: F401
from app.models.processed_image import ProcessedImage  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.recommendation import Recommendation  # noqa: F401
from app.models.report import Report  # noqa: F401
from app.models.satellite_image import SatelliteImage  # noqa: F401
from app.models.simulation import Simulation  # noqa: F401
from app.models.token import TokenBlacklist  # noqa: F401

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_optional_number")
# ...


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI.  Although available
    for the uses of...  """

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()