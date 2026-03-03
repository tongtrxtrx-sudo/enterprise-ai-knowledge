FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    markitdown \
    python-multipart \
    PyJWT \
    SQLAlchemy \
    uvicorn[standard]

COPY src /app/src
COPY scripts /app/scripts

ENV PYTHONPATH=/app/src
