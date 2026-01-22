FROM python:3.10-slim-bullseye

WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ .
COPY etl/ /app/etl/

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
