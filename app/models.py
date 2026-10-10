
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="PENDING")
    total_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    event_name = Column(String, nullable=False, default="Workshop")
    recipients = relationship(
        "Recipient",
        back_populates="job"
    )


class Recipient(Base):
    __tablename__ = "recipients"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(
        Integer,
        ForeignKey("generation_jobs.id")
    )
    name = Column(String, nullable=False)
    email = Column(String)
    certificate_id = Column(String, unique=True)
    status = Column(String, default="PENDING")
    file_path = Column(String)
    error_message = Column(String)

    job = relationship(
        "GenerationJob",
        back_populates="recipients"
    )
