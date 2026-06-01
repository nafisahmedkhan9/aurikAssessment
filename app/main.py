from fastapi import FastAPI
from app.core.database import engine, Base
from app.models import domain
from app.api.ingestion import router as ingestion_router
from app.api.output import router as output_router

# Create tables in the PostgreSQL database
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Aurik Tech Lead Assessment Backend",
    description="Industrial equipment monitoring backend service",
    version="1.0.0",
)

app.include_router(ingestion_router)
app.include_router(output_router)

@app.get("/health", tags=["Health"])
def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "message": "Backend service is running."}
