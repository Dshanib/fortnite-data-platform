-- Gold serving views (paths injected at runtime by duckdb_init.refresh_views).
-- Placeholders: {{current_island_activity}}, {{top_islands_by_peak_ccu}}, etc.

CREATE OR REPLACE VIEW vw_current_island_activity AS
SELECT * FROM read_parquet('{{current_island_activity}}');

CREATE OR REPLACE VIEW vw_top_islands_by_peak_ccu AS
SELECT * FROM read_parquet('{{top_islands_by_peak_ccu}}');

CREATE OR REPLACE VIEW vw_island_metric_hourly AS
SELECT * FROM read_parquet('{{island_metric_hourly}}');

CREATE OR REPLACE VIEW vw_shop_rarity_distribution AS
SELECT * FROM read_parquet('{{shop_rarity_distribution}}');

CREATE OR REPLACE VIEW vw_source_health_summary AS
SELECT * FROM read_parquet('{{source_health_summary}}');
