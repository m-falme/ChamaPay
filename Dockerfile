FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 \
    DATABASE_URL=sqlite:////data/chamapay.db
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /data && useradd -r -u 10001 app && chown -R app /data /app
USER app
EXPOSE 8080
# Tables are created on startup; SEED_DEMO=1 loads the demo chama.
CMD ["sh", "-c", "if [ \"$SEED_DEMO\" = \"1\" ]; then flask --app wsgi seed; fi; exec gunicorn -w 2 -b 0.0.0.0:${PORT:-8080} wsgi:app"]
