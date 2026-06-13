FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8501 \
    PRODUCTDB_USERS_PATH=/app/runtime/auth_users.json \
    PRODUCTDB_QUOTATIONS_PATH=/app/runtime/quotations \
    PRODUCTDB_LEADS_PATH=/app/runtime/leads.xlsx

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core curl \
    && rm -rf /var/lib/apt/lists/*

COPY portal_v2/requirements.txt /app/portal_v2/requirements.txt
RUN pip install --no-cache-dir -r /app/portal_v2/requirements.txt

COPY . /app
RUN mkdir -p /app/runtime/quotations

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://localhost:${PORT}/_stcore/health" || exit 1

CMD ["sh", "-c", "python -m streamlit run portal_v2/app.py --server.address=0.0.0.0 --server.port=${PORT} --server.headless=true"]
