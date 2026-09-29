FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir uv \
    && uv pip install --system --no-cache -r requirements.txt

COPY brasaland-api ./services/brasaland-api

WORKDIR /app/services/brasaland-api
EXPOSE 8010
CMD ["uvicorn", "brasaland_api.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8010", "--reload"]