FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV HOST=0.0.0.0
ENV PORT=8421
ENV OUTPUT_DIR=/app/data

RUN mkdir -p /app/data

EXPOSE 8421

CMD ["python", "dashboard.py"]
