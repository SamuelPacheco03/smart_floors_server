import os
from fastapi import FastAPI
import uvicorn
from sqlalchemy import create_engine
from app.db.session import check_connection, engine, Base
from app.api.v1.router import api_router

async def lifespan(app: FastAPI):
    try:
        check_connection()
        print("✅ Conexión a PostgreSQL establecida correctamente.")
    except Exception as e:
        print(f"❌ Error conectando a la base de datos: {e}")
        raise e

    yield 

    try:
        engine.dispose()
        print("🧹 Conexión a PostgreSQL cerrada.")
    except Exception as e:
        print(f"⚠️ Error al cerrar conexión: {e}")
        
app = FastAPI(lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"Hello": "World"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)