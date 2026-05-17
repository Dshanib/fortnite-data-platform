"""Domain-specific exceptions."""


class ConfigError(Exception):
    """Raised when configuration is missing or invalid."""


class ValidationError(Exception):
    """Raised when data validation fails."""


class IngestionError(Exception):
    """Raised when ingestion cannot complete."""


class StorageError(Exception):
    """Raised when object storage operations fail."""


class ApiClientError(Exception):
    """Raised when an HTTP API call fails after retries."""


class ScrapeClientError(Exception):
    """Raised when scraping fails."""


class KafkaProducerError(Exception):
    """Raised when Kafka publish fails."""


class QueryServiceError(Exception):
    """Raised when a predefined query cannot execute."""
