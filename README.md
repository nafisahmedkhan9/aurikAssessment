# Aurik Industrial Monitoring Backend

This is the backend service for processing operational machine data from various vendors. It handles data ingestion, normalization, deterministic state derivation, and exposes operational API views.

## Architecture & Design Decisions
1. **Pydantic Validation**: Used heavily at the ingestion boundary to ensure strict compliance with expected schemas.
2. **PostgreSQL Persistence**: Replaced SQLite with PostgreSQL for production readiness, maintaining raw payload traceability in `IngestedPayload` and normalized data in `NormalizedEvent`.
3. **Idempotency**: Event UUIDs act as primary keys in `NormalizedEvent`. Utilizing `db.merge()` ensures safe re-ingestion of identical batches.
4. **Deterministic State Derivation**: The background task derives states cleanly from `NormalizedEvent` records, mapping raw data strictly to defined Enums (`SeverityLevel`, `DerivedStatus`). No ML or non-deterministic approaches are utilized.

## Assumptions & Trade-Offs
- **Idempotency over strict chronological ordering:** `db.merge()` is used to gracefully update normalized events on duplicate ingestion, assuming that vendors might replay data.
- **Background Tasks over Message Queues:** In a massive scale system, Kafka or RabbitMQ would be used for ingestion. For this assessment, FastAPI's built-in `BackgroundTasks` was chosen to keep the architecture simple, clean, and easily runnable without heavy infrastructure.
- **Synchronous SQLAlchemy over AsyncPG:** SQLAlchemy is used synchronously. While `asyncpg` offers better throughput, synchronous is easier to reason about for deterministic rules and is entirely sufficient given the background task offloading.

## Limitations & Next Steps for Production
1. **Authentication/Authorization:** The APIs are currently completely open. In production, an API Gateway or JWT token validation would be added to the `/api/v1/ingest` endpoints to verify vendor identities.
2. **Dedicated Message Broker:** Transitioning from `BackgroundTasks` to Celery or an external queue (e.g., SQS/Kafka) to ensure payloads aren't lost if the FastAPI pod crashes before processing is complete.
3. **Database Migrations:** Implementing `Alembic` to manage database schema evolutions over time instead of relying on `Base.metadata.create_all()`.
4. **Caching Layer:** Adding Redis to cache the Plant Summary endpoints if the database grows large.

## Running Locally via Docker Compose
To run both the application and the database natively through Docker:
```bash
docker compose up --build -d
```
The API Swagger documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Running Locally via Venv (Dev Mode)
1. Start only the database: `docker compose up db -d`
2. Install dependencies: `pip install -r requirements.txt`
3. Run FastAPI: `uvicorn app.main:app --reload`

## Testing
Run `pytest` to execute unit tests inside the `/backend` directory:
```bash
pytest
```
