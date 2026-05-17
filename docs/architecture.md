# Architecture (Phase 1)

## Overview

Phase 1 implements a modular Fortnite data platform foundation:

```
Sources → Ingestion → Kafka → (future consumers) → MinIO bronze
                                              ↘
                                        DuckDB serving → Telegram bot
```

## Layers

| Layer | Package | Responsibility |
|-------|---------|----------------|
| Config | `config/settings.py` | Typed settings, validation, single env access point |
| Common | `common/` | Models, validators, logging, exceptions |
| Ingestion | `ingestion/` | CCU, shop, cosmetics pipelines |
| Producers | `producers/` | Kafka JSON producer |
| Storage | `storage/` | MinIO client, paths, bronze writers, health |
| Serving | `serving/` | DuckDB init, predefined queries |
| Bot | `bot/` | Telegram intents → `query_service` only |

## Design rules

- No PySpark in Phase 1
- No ad-hoc SQL from the bot
- No `os.getenv` outside `config/settings.py`
- No secrets in git; example env files only
- No side effects on import (entrypoints call `main()` / `run_ingestion()`)

## Kafka topics

| Topic | Purpose |
|-------|---------|
| `fortnite.raw.ccu` | CCU snapshots |
| `fortnite.raw.shop` | Item shop payloads |
| `fortnite.raw.cosmetics` | Cosmetics catalog |
| `fortnite.ops.ingestion_status` | Source health events |

## MinIO profiles

- **internal**: local Docker MinIO (`localhost:9000`)
- **external**: remote MinIO on LAN (`192.168.x.x:9000`)

Switch via `MINIO_PROFILE` and endpoint credentials in `.env`.

## Excluded (later phases)

- PySpark jobs
- NLP-to-SQL
- Dashboards
- Airflow
- Cloud production deployment
