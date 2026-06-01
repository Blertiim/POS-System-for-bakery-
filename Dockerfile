FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000
ENV BAKERY_POS_DB=/data/bakery_pos.db

WORKDIR /app

COPY app ./app
COPY static ./static
COPY run.py ./run.py

RUN mkdir -p /data

VOLUME ["/data"]
EXPOSE 8000

CMD ["python", "run.py"]

