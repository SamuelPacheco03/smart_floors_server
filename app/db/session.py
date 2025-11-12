from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine = create_engine(
    settings.db_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

Base = declarative_base()


def check_connection() -> None:
    """
    Intento simple de conexión para validar credenciales/red.
    Lanza excepción si falla.
    """
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
