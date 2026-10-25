FROM python:3.12-slim

RUN groupadd --system --gid 10001 brasaland \
    && useradd --system --uid 10001 --gid brasaland --home-dir /var/lib/brasaland --create-home --shell /usr/sbin/nologin brasaland \
    && mkdir -p /var/lib/brasaland \
    && chown -R brasaland:brasaland /var/lib/brasaland

ENV HOME=/var/lib/brasaland \
    TINYDB_PATH=/var/lib/brasaland/db.json \
    RFP_CHECKPOINT_PATH=/var/lib/brasaland/rfp_approval_checkpoints.sqlite3 \
    AGENT_MEMORY_DB_PATH=/var/lib/brasaland/agent_memory.sqlite3 \
    CHAT_SESSION_DB_PATH=/var/lib/brasaland/chat_sessions.sqlite3 \
    RFP_UPLOAD_DIRECTORY=/var/lib/brasaland/rfp-intake

WORKDIR /app

COPY services/requirements.txt ./services/requirements.txt
RUN pip install --no-cache-dir uv \
    && uv pip install --system --no-cache -r ./services/requirements.txt

COPY packages/shared ./packages/shared
RUN uv pip install --system --no-cache ./packages/shared

COPY services/brasaland-api ./services/brasaland-api

WORKDIR /app/services/brasaland-api
EXPOSE 8010
USER brasaland:brasaland
CMD ["uvicorn", "brasaland_api.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8010"]