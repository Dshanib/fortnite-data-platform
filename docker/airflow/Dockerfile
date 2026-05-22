# Extend official Airflow image with project Python dependencies.
# Pipeline steps run as subprocess calls to existing scripts (--engine python).
# PySpark JVM batch is not required inside this image for scheduled refreshes.
FROM apache/airflow:2.9.3-python3.11

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir "psycopg2-binary>=2.9.9"

ENV FORTNITE_PROJECT_ROOT=/opt/airflow/project \
    PYTHONPATH=/opt/airflow/project
