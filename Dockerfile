FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e ".[postgres]"

EXPOSE 8080
CMD ["uvicorn", "shadow_server.app:app", "--host", "0.0.0.0", "--port", "8080"]
