FROM python:3.12.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y sqlite3

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "pytest --maxfail=1 --disable-warnings --capture=tee-sys && python create_tables.py && uvicorn main:app --host 0.0.0.0 --port 8000"]
