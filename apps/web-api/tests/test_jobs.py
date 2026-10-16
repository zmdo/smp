import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("INTERNAL_TOKEN", "unused")
os.environ.setdefault("SESSION_SECRET", "unused")
os.environ.setdefault("ADMIN_PASSWORD", "unused")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from smp_web.routers.jobs import get_job
from smpcore.models import Base, OpsJob, Server


def test_job_status_accepts_the_id_returned_to_the_page():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    server = Server(
        name="sg",
        intranet_host="43.128.69.189",
        ssh_port=22,
        ssh_user="ubuntu",
        auth_method="private_key",
        secret_ciphertext="",
        reachability="unknown",
    )
    session.add(server)
    session.flush()
    job = OpsJob(server_id=server.id, action="install_components", status="running", output_excerpt="")
    session.add(job)
    session.commit()

    found = get_job(str(job.id), session)

    assert found["id"] == job.id
    assert found["status"] == "running"
    assert found["action"] == "install_components"
