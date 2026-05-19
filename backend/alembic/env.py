from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.core.config import settings

# 명시적 SQL 마이그레이션 — 모델 import 금지
# asyncpg는 multi-statement DDL을 prepared statement로 처리할 수 없으므로
# 마이그레이션 실행 시에는 psycopg2(동기) 드라이버를 사용한다.
target_metadata = None

config = context.config

sync_url = settings.database_url.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)
config.set_main_option("sqlalchemy.url", sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(sync_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
