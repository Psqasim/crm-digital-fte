FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY production/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# HF Spaces requires port 7860
EXPOSE 7860

CMD ["uvicorn", "production.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
