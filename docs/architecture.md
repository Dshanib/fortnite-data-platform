# Architecture (Phase 1)

## Overview

Phase 1 implements a modular Fortnite data platform with **two API-based sources** (no scraping in the primary path):

```
Fortnite-API.com          Fortnite Ecosystem API
(shop, cosmetics)    →    (islands, engagement metrics)
         ↓                           ↓
              Ingestion → Kafka → (future) → MinIO bronze
                                              ↘ DuckDB serving → Telegram bot
```

**Documentation:** [Fortnite Ecosystem API](https://api.fortnite.com/ecosystem/v1/docs/)

## Data sources

| Source | Base URL | Purpose |
|--------|----------|---------|
| **Fortnite-API.com** | `https://fortnite-api.com` | Static/reference data: item shop snapshots, cosmetics catalog, item metadata |
| **Fortnite Ecosystem API** | `https://api.fortnite.com/ecosystem/v1` | Dynamic island engagement: peak CCU, unique players, plays, minutes played |

**Not in primary architecture:** web scraping (Fortnite.gg or HTML scrape). `scrape_client.py` is deprecated legacy only.

## Ingestion pipelines

| Module | API | Endpoints | Kafka topic |
|--------|-----|-----------|-------------|
| `ingest_shop.py` | Fortnite-API.com | `GET /v2/shop` | `fortnite.raw.shop` |
| `ingest_cosmetics.py` | Fortnite-API.com | `GET /v2/cosmetics/br` | `fortnite.raw.cosmetics` |
| `ingest_islands.py` | Ecosystem | `GET /islands` | `fortnite.raw.islands` |
| `ingest_island_metrics.py` | Ecosystem | `GET /islands/{code}/metrics/{interval}` (+ per-metric paths) | `fortnite.raw.island_metrics` |

`ingest_ccu.py` is **deprecated**; peak CCU is ingested via `ingest_island_metrics`.

## API clients

- `ingestion/clients/fortnite_api_client.py` — Fortnite-API.com
- `ingestion/clients/ecosystem_api_client.py` — Ecosystem API (optional Epic OAuth)

## Layers

| Layer | Package | Responsibility |
|-------|---------|----------------|
| Config | `config/settings.py` | Typed settings, validation |
| Common | `common/` | Models, validators, logging |
| Ingestion | `ingestion/` | API-based pipelines |
| Producers | `producers/` | Kafka JSON producer |
| Storage | `storage/` | MinIO (future bronze writes) |
| Serving | `serving/` | DuckDB scaffold / mock queries |
| Bot | `bot/` | Telegram → `query_service` only |

## Kafka topics

| Topic | Purpose |
|-------|---------|
| `fortnite.raw.shop` | Item shop snapshots |
| `fortnite.raw.cosmetics` | Cosmetics catalog |
| `fortnite.raw.islands` | Island catalog |
| `fortnite.raw.island_metrics` | Engagement metrics per island |
| `fortnite.ops.ingestion_status` | Pipeline health events |

## Authentication

- **Fortnite-API.com:** optional `FORTNITE_API_KEY` (Authorization header)
- **Ecosystem API:** optional `FORTNITE_CLIENT_ID` / `FORTNITE_CLIENT_SECRET` (Epic OAuth). On `401`/`403`, clients report that auth is required.

## Bot (unchanged behavior)

Telegram bot uses mock/predefined `query_service` queries. Future intents may include island-level metrics once DuckDB is populated.

## Excluded (later phases)

- PySpark, Airflow, dashboards, NLP-to-SQL, production cloud deployment
