FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /src/web-api

COPY packages/smpcore /src/smpcore
COPY apps/web-api /src/web-api

RUN pip install --no-cache-dir /src/smpcore .

EXPOSE 8000

CMD ["uvicorn", "smp_web.main:app", "--host", "0.0.0.0", "--port", "8000"]
