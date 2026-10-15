FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /src/ops

COPY packages/smpcore /src/smpcore
COPY apps/ops /src/ops

RUN pip install --no-cache-dir /src/smpcore .

EXPOSE 8081

CMD ["uvicorn", "smp_ops.main:app", "--host", "0.0.0.0", "--port", "8081"]
