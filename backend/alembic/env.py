from logging.config import fileConfig

import os, sys
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy import pool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.database import Base
from alembic import context

from app.models.user import User
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.relationship import Relationship
from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.models.chat import Chat
from app.models.chat_member import ChatMember
from app.models.message import Message
from app.models.album import Album
from app.models.photo import Photo
from app.models.album_member import AlbumMember
from app.models.invitation_code import InvitationCode

from app.core.config import settings
DATABASE_URL = settings.DATABASE_URL

load_dotenv()


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = create_engine(
        DATABASE_URL,
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
