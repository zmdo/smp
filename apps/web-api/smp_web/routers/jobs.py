import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from smp_web.deps import get_session, job_out, require_user
from smp_web.schemas import JobOut
from smpcore.models import OpsJob

router = APIRouter(prefix="/api/ops-jobs", dependencies=[Depends(require_user)])


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        parsed = uuid.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="任务不存在") from exc
    job = session.get(OpsJob, parsed)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job_out(job)
