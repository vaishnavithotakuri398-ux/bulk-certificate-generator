
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List
from app.database import engine, Base, SessionLocal
from app.models import GenerationJob, Recipient
from app.certificate_service import generate_certificate
import uuid

from fastapi.responses import FileResponse
from pathlib import Path


import io
import pandas as pd

from fastapi import UploadFile, File, Form


from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import io
import zipfile

from fastapi.responses import StreamingResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bulk Certificate Generator")

BASE_DIR = Path(__file__).resolve().parent.parent

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(BASE_DIR / "templates" / "index.html")


# Database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Request models
class RecipientInput(BaseModel):
    name: str = Field(min_length=1)
    email: str


class JobInput(BaseModel):
    event_name: str = Field(min_length=1)
    recipients: List[RecipientInput] = Field(min_length=1)


# Home endpoint
@app.get("/")
def home():
    return {"message": "Certificate Generator API is running"}


# Create a bulk generation job
@app.post("/api/jobs/", status_code=201)
def create_job(data: JobInput, db: Session = Depends(get_db)):
    job = GenerationJob(
        status="PENDING",
        total_count=len(data.recipients),
        success_count=0,
        failure_count=0
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    for item in data.recipients:
        recipient = Recipient(
            job_id=job.id,
            name=item.name.strip(),
            email=item.email
        )
        db.add(recipient)

    db.commit()
    db.refresh(job)

    return {
        "job_id": job.id,
        "event_name": data.event_name,
        "status": job.status,
        "total_count": job.total_count,
        "success_count": job.success_count,
        "failure_count": job.failure_count
    }


# Get job status
@app.get("/api/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(GenerationJob).filter(
        GenerationJob.id == job_id
    ).first()

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    return {
        "job_id": job.id,
        "status": job.status,
        "total_count": job.total_count,
        "success_count": job.success_count,
        "failure_count": job.failure_count
    }

# Generate certificates for all recipients in a job
@app.post("/api/jobs/{job_id}/generate")
def generate_job_certificates(
    job_id: int,
    db: Session = Depends(get_db)
):
    job = db.query(GenerationJob).filter(
        GenerationJob.id == job_id
    ).first()

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    recipients = db.query(Recipient).filter(
        Recipient.job_id == job_id
    ).all()

    if not recipients:
        raise HTTPException(
            status_code=400,
            detail="No recipients found for this job"
        )

    # Find the event name from the job request.
    # Store it in the job model in the next improvement.
    event_name = job.event_name

    success_count = 0
    failure_count = 0
    results = []

    for recipient in recipients:
        try:
            if not recipient.certificate_id:
                recipient.certificate_id = str(uuid.uuid4())

            file_path = generate_certificate(
                recipient.name,
                event_name,
                recipient.certificate_id
            )

            recipient.file_path = file_path
            recipient.status = "SUCCESS"
            recipient.error_message = None
            success_count += 1

            results.append({
                "recipient_id": recipient.id,
                "name": recipient.name,
                "status": "SUCCESS"
            })

        except Exception as exc:
            recipient.status = "FAILED"
            recipient.error_message = str(exc)
            failure_count += 1

            results.append({
                "recipient_id": recipient.id,
                "name": recipient.name,
                "status": "FAILED",
                "error": str(exc)
            })

    job.success_count = success_count
    job.failure_count = failure_count
    job.status = (
        "COMPLETED_WITH_ERRORS"
        if failure_count > 0
        else "COMPLETED"
    )

    db.commit()

    return {
        "job_id": job.id,
        "status": job.status,
        "total_count": len(recipients),
        "success_count": success_count,
        "failure_count": failure_count,
        "results": results
    }
    
# Download an individual generated certificate
@app.get("/api/recipients/{recipient_id}/download")
def download_certificate(
    recipient_id: int,
    db: Session = Depends(get_db)
):
    recipient = db.query(Recipient).filter(
        Recipient.id == recipient_id
    ).first()

    if recipient is None:
        raise HTTPException(
            status_code=404,
            detail="Recipient not found"
        )

    if not recipient.file_path:
        raise HTTPException(
            status_code=404,
            detail="Certificate has not been generated"
        )

    file_path = Path(recipient.file_path)

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Certificate file not found"
        )

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=file_path.name
    )

@app.post("/api/jobs/upload", status_code=201)
async def upload_recipients(
    event_name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Check file extension
    filename = (file.filename or "").lower()

    if not filename.endswith((".csv", ".xlsx")):
        raise HTTPException(
            status_code=400,
            detail="Upload a .csv or .xlsx file"
        )

    # Read uploaded file
    contents = await file.read()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Unable to read the uploaded file"
        )

    # Normalize column names
    df.columns = [
        str(column).strip().lower()
        for column in df.columns
    ]

    if "name" not in df.columns or "email" not in df.columns:
        raise HTTPException(
            status_code=400,
            detail="File must contain name and email columns"
        )

    # Validate recipient rows
    recipients_data = []

    for index, row in df.iterrows():
        name = row["name"]
        email = row["email"]

        if pd.isna(name) or pd.isna(email):
            raise HTTPException(
                status_code=400,
                detail=f"Missing name or email in row {index + 2}"
            )

        name = str(name).strip()
        email = str(email).strip()

        if not name or not email or "@" not in email:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid name or email in row {index + 2}"
            )

        recipients_data.append({
            "name": name,
            "email": email
        })

    if not recipients_data:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file contains no recipients"
        )

    # Create job
    job = GenerationJob(
        event_name=event_name,
        status="PENDING",
        total_count=len(recipients_data),
        success_count=0,
        failure_count=0
    )

    db.add(job)
    db.flush()

    # Save recipients
    for item in recipients_data:
        recipient = Recipient(
            job_id=job.id,
            name=item["name"],
            email=item["email"],
            status="PENDING"
        )
        db.add(recipient)

    db.commit()
    db.refresh(job)

    return {
        "message": "Recipients uploaded successfully",
        "job_id": job.id,
        "event_name": job.event_name,
        "status": job.status,
        "total_count": job.total_count
    }

@app.post("/api/jobs/upload-and-generate", status_code=201)
async def upload_and_generate(
    event_name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Reuse the existing upload endpoint
    result = await upload_recipients(
        event_name=event_name,
        file=file,
        db=db
    )

    # Generate certificates for the new job
    job_id = result["job_id"]

    generation_result = generate_job_certificates(
        job_id=job_id,
        db=db
    )

    return {
        "message": "Upload and certificate generation completed",
        "job_id": job_id,
        "event_name": event_name,
        "upload": result,
        "generation": generation_result
    }

@app.get("/api/certificates/download-all")
def download_all_certificates():
    certificates_dir = BASE_DIR / "generated_certificates"

    if not certificates_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Certificates folder not found"
        )

    pdf_files = list(certificates_dir.rglob("*.pdf"))

    if not pdf_files:
        raise HTTPException(
            status_code=404,
            detail="No generated certificates found"
        )

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(
        zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as zip_file:
        for pdf_path in pdf_files:
            # Preserve subfolders if certificates are organized by job.
            arcname = pdf_path.relative_to(certificates_dir)
            zip_file.write(pdf_path, arcname=str(arcname))

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition":
                'attachment; filename="all_certificates.zip"'
        },
    )
