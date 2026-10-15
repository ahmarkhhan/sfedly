FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    SKONY_MODE=replay \
    SKONY_DATA_DIR=/state

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends poppler-utils fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 skony \
    && useradd --uid 10001 --gid skony --no-create-home skony \
    && mkdir /state \
    && chown skony:skony /state

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY web/ ./web/
COPY tests/ ./tests/
COPY scripts/ ./scripts/
COPY data/sample/ ./data/sample/
COPY LICENSE ./LICENSE

USER skony
EXPOSE 8765

HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=5 \
    CMD ["python", "scripts/healthcheck.py"]

CMD ["python", "-m", "skony", "serve", "--host", "0.0.0.0", "--port", "8765"]
