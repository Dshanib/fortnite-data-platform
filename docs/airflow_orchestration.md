# Airflow orchestration

## Why Airflow

The Fortnite lakehouse pipeline (APIs → Kafka → Bronze → Silver → Gold → DuckDB) was proven end-to-end with `scripts/demo_run.py`. Periodic refreshes previously used `scripts/continuous_refresh.py`, which is a simple loop and not suitable for production scheduling.

**Apache Airflow** is now the official orchestration layer:

- Separate schedules per domain (metrics, shop, reference data)
- Retries, timeouts, and `max_active_runs=1` to avoid overlapping refreshes
- UI for manual triggers, logs, and task-level retries
- DAG code only **coordinates** existing scripts — no duplicated pipeline logic

## Pipeline vs orchestration

| Layer | Responsibility | Location |
|-------|----------------|----------|
| Ingestion | Call Fortnite APIs, publish Kafka | `ingestion/` |
| Bronze | Consume Kafka → MinIO JSON | `scripts/kafka_to_bronze_once.py` |
| Silver / Gold | Batch transforms | `scripts/run_bronze_to_silver.py`, `scripts/run_silver_to_gold.py` |
| Serving | DuckDB views over Gold | `serving/`, `scripts/check_duckdb_serving.py` |
| **Orchestration** | When and in what order steps run | `dags/`, Airflow |

Airflow tasks use **BashOperator** to run the same Python entry points you use locally. Inside Docker, tasks use `--engine python` (PyArrow/MinIO), not an in-container Spark JVM.

## DAGs

| DAG ID | Schedule | Purpose |
|--------|----------|---------|
| `fortnite_full_demo_dag` | Manual only (`schedule=None`) | Full pipeline demo (like `demo_run.py`) |
| `fortnite_metrics_refresh_dag` | Every **5** minutes | Island metrics + lake refresh |
| `fortnite_shop_refresh_dag` | Every **60** minutes | Shop snapshot |
| `fortnite_reference_refresh_dag` | Every **24** hours | Cosmetics + islands reference |

All DAGs use tags: `fortnite`, `data-engineering`, `refresh`.

Shared defaults (environment variables):

| Variable | Default | Meaning |
|----------|---------|---------|
| `FORTNITE_MAX_ISLANDS` | `50` | Cap for `ingest_island_metrics` |
| `FORTNITE_SERVING_MODE` | `direct_minio` | DuckDB Gold read mode |
| `FORTNITE_MAX_MESSAGES_PER_TOPIC` | `20` | Kafka → Bronze batch size per topic |

In Docker Compose, Airflow also sets:

- `KAFKA_BOOTSTRAP_SERVERS=kafka:29092`
- `MINIO_ENDPOINT=http://minio:9000`
- `FORTNITE_PROJECT_ROOT=/opt/airflow/project`

Host-side scripts (bot, manual CLI) keep using `localhost` from `.env`.

## Replacing `continuous_refresh.py`

`scripts/continuous_refresh.py` was moved to **`scripts/deprecated/continuous_refresh.py`**.

- **Primary scheduler:** Airflow DAGs above
- **Manual one-shot:** `python scripts/demo_run.py --serving-mode direct_minio`
- **Fallback debugging:** deprecated script (prints a warning)

## Runtime layout

```text
Terminal 1:  docker compose --env-file .env up -d
Terminal 2:  python -m bot.app
Airflow:     scheduled DAGs (web UI http://localhost:8080)
```

The Telegram bot does **not** write data; it reads Gold via DuckDB. Airflow keeps Gold fresh.

## Airflow UI

1. Start stack (see README).
2. Open http://localhost:8080
3. Login: `admin` / `admin` (override with `_AIRFLOW_WWW_USER_USERNAME` / `_AIRFLOW_WWW_USER_PASSWORD` in `.env`)

### Manual demo DAG

1. Unpause **`fortnite_full_demo_dag`** if paused.
2. Trigger DAG (play button).
3. Open Graph → click a task → **Log** for stdout/stderr.

### Inspect failures

- Red task in graph → open **Log**
- Use **Clear** / **Retry** on failed task after fixing infra or API limits
- Scheduler log: `docker logs fortnite-airflow-scheduler`

## Docker Compose notes

- Airflow services use the **`airflow` profile** so `docker compose up -d` starts only Kafka/MinIO without pulling Postgres.
- Metadata DB uses **`postgres:13`** (commonly cached locally). Avoid `postgres:16` if Docker Hub pulls fail with EOF errors.
- Set **`AIRFLOW_FERNET_KEY`** and **`AIRFLOW_UID=0`** in **`.env` only** (never commit `.env` or paste keys into tests/docs).
- Always pass **`--env-file .env`** so Compose reads your Fernet key.
- If a Fernet key was ever pushed to Git, **rotate it** (generate a new value, update `.env`, restart Airflow) and scrub git history.

```bash
docker compose --env-file .env --profile airflow up -d --build
```

## Known limitations

- **PySpark (`--engine spark`)** is not run inside the Airflow image by default; scheduled jobs use `--engine python`.
- **DuckDB + MinIO** from Airflow use the container network (`minio:9000`). The bot on the host still uses `localhost:9000` from `.env`.
- **API rate limits** apply; metrics DAG may run up to 90 minutes timeout for large island batches.
- **First Airflow start** requires `airflow-init` to migrate DB and create the admin user.
- DAGs are **paused at creation** until you unpause them in the UI (configurable via `AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION`).

## File layout

```text
dags/                          # Airflow DAG definitions only
orchestration/                 # Shared BashOperator factories
docker/airflow/Dockerfile      # Airflow image + requirements.txt
scripts/demo_run.py            # Manual full pipeline (kept)
scripts/deprecated/            # Old continuous_refresh.py
```
