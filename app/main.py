import os
from fastapi import FastAPI
import uvicorn
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import check_connection, engine, Base
from app.api.v1.router import api_router

from app.db.models import building, floor, metric, threshold, alert 

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle moderno de FastAPI (reemplaza startup/shutdown)
    """
    try:
        # 1️ Verificar conexión a la base de datos
        check_connection()
        print("Conexión a PostgreSQL establecida correctamente.")

        # 2️ Crear tablas si no existen
        print("Verificando existencia de tablas...")
        Base.metadata.create_all(bind=engine)
        print("Tablas verificadas / creadas correctamente.")
    except SQLAlchemyError as e:
        print(f"Error de SQLAlchemy: {e}")
        raise e
    except Exception as e:
        print(f"Error general conectando a la base de datos: {e}")
        raise e

    # yield = mientras la app esté corriendo
    yield

    # 3️Cierre limpio
    try:
        engine.dispose()
        print("Conexión a PostgreSQL cerrada.")
    except Exception as e:
        print(f"Error al cerrar conexión: {e}")


# ======================================================
# Inicializar aplicación
# ======================================================

app = FastAPI(lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "API SmartFloors activa ✅"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
