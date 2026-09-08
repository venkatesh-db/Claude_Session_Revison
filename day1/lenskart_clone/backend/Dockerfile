FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV FLASK_RUN_HOST=0.0.0.0
EXPOSE 5000

CMD ["python", "app.py"]
