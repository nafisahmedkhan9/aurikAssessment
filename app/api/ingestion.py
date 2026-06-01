import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.api import schemas
from app.core.database import get_db
from app.models.domain import IngestedPayload, ProcessingStatus

router = APIRouter(prefix="/api/v1/ingest", tags=["Ingestion"])

def store_raw_payload(db: Session, vendor: str, raw_json: str) -> str:
    """Stores the raw JSON into the database for traceability and idempotency."""
    payload_id = str(uuid.uuid4())
    payload = IngestedPayload(
        payload_id=payload_id,
        vendor=vendor,
        raw_data=raw_json,
        status=ProcessingStatus.PENDING
    )
    db.add(payload)
    db.commit()
    return payload_id

from app.services.normalization import process_payload_task

@router.post("/pulseforge", response_model=schemas.IngestionResponse)
def ingest_pulseforge(
    payload: schemas.PulseForgePayload, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Pydantic has already validated the schema perfectly!
    payload_id = store_raw_payload(db, "PulseForge", payload.model_dump_json())
    
    # Offload processing to background
    background_tasks.add_task(process_payload_task, payload_id)
    
    return schemas.IngestionResponse(payload_id=payload_id, message="Payload accepted for processing")

@router.post("/thermexwatch", response_model=schemas.IngestionResponse)
def ingest_thermexwatch(
    payload: schemas.ThermexWatchPayload, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    payload_id = store_raw_payload(db, "ThermexWatch", payload.model_dump_json())
    background_tasks.add_task(process_payload_task, payload_id)
    return schemas.IngestionResponse(payload_id=payload_id, message="Payload accepted for processing")

@router.post("/maintaflow", response_model=schemas.IngestionResponse)
def ingest_maintaflow(
    payload: schemas.MaintaFlowPayload, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    payload_id = store_raw_payload(db, "MaintaFlow", payload.model_dump_json())
    background_tasks.add_task(process_payload_task, payload_id)
    return schemas.IngestionResponse(payload_id=payload_id, message="Payload accepted for processing")
