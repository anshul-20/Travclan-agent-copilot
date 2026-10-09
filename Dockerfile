FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
# Add sentence-transformers here for real MiniLM embeddings (large download): pip install sentence-transformers
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY scripts ./scripts
ENV PYTHONPATH=/app/backend
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
