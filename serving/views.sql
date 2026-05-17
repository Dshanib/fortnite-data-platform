-- Predefined DuckDB views for Phase 1 serving layer.
-- Tables are populated by downstream pipelines; views degrade gracefully when missing.

CREATE OR REPLACE VIEW v_ccu_current AS
SELECT player_count, captured_at
FROM ccu_snapshots
ORDER BY captured_at DESC
LIMIT 1;

CREATE OR REPLACE VIEW v_ccu_daily_avg AS
SELECT AVG(player_count) AS avg_ccu
FROM ccu_snapshots
WHERE CAST(captured_at AS DATE) = CURRENT_DATE;

CREATE OR REPLACE VIEW v_ccu_anomalies AS
SELECT player_count, captured_at, z_score
FROM ccu_anomalies
ORDER BY captured_at DESC
LIMIT 10;

CREATE OR REPLACE VIEW v_shop_rarity AS
SELECT rarity, COUNT(*) AS item_count
FROM shop_items
GROUP BY rarity;

CREATE OR REPLACE VIEW v_source_health AS
SELECT source, entity, status, message, observed_at
FROM source_health_events
ORDER BY observed_at DESC
LIMIT 20;
