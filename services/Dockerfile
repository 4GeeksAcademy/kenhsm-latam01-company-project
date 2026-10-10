FROM python:3.12-slim

WORKDIR /app

COPY services/requirements.txt ./services/requirements.txt
RUN pip install --no-cache-dir uv \
    && uv pip install --system --no-cache -r ./services/requirements.txt

COPY packages/shared ./packages/shared
RUN uv pip install --system --no-cache ./packages/shared

COPY services/brasaland-api ./services/brasaland-api

WORKDIR /app/services/brasaland-api
EXPOSE 8010
CMD ["uvicorn", "brasaland_api.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8010", "--reload"]