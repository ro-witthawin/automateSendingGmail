# ===== 1. Base image =====
FROM python:3.11-slim

# ===== 2. Workdir =====
WORKDIR /app

# ===== 3. System deps (optional but useful for google-api-python-client) =====
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ===== 4. Copy requirements and install =====
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ===== 5. Copy source code =====
# assuming your structure:
# .
# ├── app/
# │   ├── main.py
# │   └── email_utils.py
# ├── requirements.txt
# └── .env (mounted at runtime)
COPY app ./app

# ===== 6. Env (can be overridden at runtime) =====
ENV PYTHONUNBUFFERED=1
# You can set a default, but better to pass via docker run / compose
# ENV SERVICE_ACCOUNT_FILE=/secrets/service-account.json
# ENV DELEGATED_USER=you@your-edu-domain.ac.th

# ===== 7. Expose port =====
EXPOSE 8000

# ===== 8. Run app =====
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

