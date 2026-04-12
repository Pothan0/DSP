FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV TRUSTCHAIN_MCP_PORT=7070
ENV TRUSTCHAIN_TELEMETRY_PROMETHEUS_ENABLED=true

EXPOSE 7070 9090

CMD ["python", "gateway/app.py"]