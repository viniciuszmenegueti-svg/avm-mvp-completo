FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system avm \
    && adduser --system --ingroup avm avm

COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY alembic.ini .
COPY migrations ./migrations
COPY app ./app
COPY docker-entrypoint.sh .

RUN chmod +x /app/docker-entrypoint.sh \
    && chown -R avm:avm /app

USER avm

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
