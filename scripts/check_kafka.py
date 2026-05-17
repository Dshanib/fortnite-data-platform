#!/usr/bin/env python3
"""Validate Kafka producer connectivity with a test event."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from kafka.errors import NoBrokersAvailable

from scripts._script_runtime import bootstrap, safe_print

bootstrap()

from common.exceptions import KafkaProducerError
from common.logging import configure_logging, get_logger
from common.models import utc_now_iso
from config.settings import get_settings
from producers.kafka_producer import FortniteKafkaProducer

logger = get_logger(__name__)


def main() -> int:
    """Send a small JSON test event to the ingestion status topic."""
    producer = None
    try:
        settings = get_settings()
        configure_logging(settings.log_level)
        topic = settings.kafka_topic_ingestion_status
        timestamp = utc_now_iso()

        safe_print(f"Kafka bootstrap: {settings.kafka_bootstrap_servers}")
        safe_print(f"Test topic: {topic}")
        safe_print(f"Timestamp: {timestamp}")

        producer = FortniteKafkaProducer(settings)
        event = {
            "source": "check_kafka",
            "entity": "connectivity",
            "status": "success",
            "message": "kafka producer connectivity test",
            "observed_at": timestamp,
        }
        producer.send_event(topic, event, key="connectivity-test")
        producer.flush()

        safe_print("Kafka producer connectivity: SUCCESS")
        return 0
    except NoBrokersAvailable:
        safe_print("Kafka connection failed: no broker available.")
        safe_print("Start infra: docker compose --env-file .env up -d zookeeper kafka")
        return 1
    except KafkaProducerError as exc:
        safe_print(f"Kafka producer connectivity: FAILED — {exc}")
        return 1
    except Exception as exc:
        safe_print(f"Kafka producer connectivity: FAILED — {exc}")
        logger.exception("check_kafka failed")
        return 1
    finally:
        if producer is not None:
            producer.close()


if __name__ == "__main__":
    sys.exit(main())
