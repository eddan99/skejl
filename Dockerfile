FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

RUN mkdir -p data/input data/output data/models

# Chainlit writes .files/ at startup — needs a writable home
ENV HOME=/tmp

# Cloud Run injects PORT; Chainlit honours it via --port
ENV PORT=8080

EXPOSE 8080

CMD chainlit run ui/app.py --host 0.0.0.0 --port $PORT
