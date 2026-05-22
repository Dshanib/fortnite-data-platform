"""Descriptive parquet object names for MinIO (avoid generic data.parquet)."""


def dataset_parquet_filename(dataset: str) -> str:
    """Single-file parquet name, e.g. shop_items.parquet."""
    safe = dataset.strip("/").replace("/", "_")
    return f"{safe}.parquet"


def dataset_partition_basename_template(dataset: str) -> str:
    """PyArrow partition file template, e.g. island_metrics-part-{i}.parquet."""
    safe = dataset.strip("/").replace("/", "_")
    return f"{safe}-part-{{i}}.parquet"
