ALTER TABLE accounts ADD COLUMN monitor_average_duration_ms INTEGER;

WITH ranked AS (
    SELECT account_id,
           duration_ms,
           ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY checked_at DESC, id DESC) AS row_number
    FROM monitor_records
    WHERE duration_ms IS NOT NULL
), averages AS (
    SELECT account_id,
           CAST(ROUND(AVG(duration_ms)) AS INTEGER) AS monitor_average_duration_ms
    FROM ranked
    WHERE row_number <= 30
    GROUP BY account_id
)
UPDATE accounts
SET monitor_average_duration_ms = (
    SELECT averages.monitor_average_duration_ms
    FROM averages
    WHERE averages.account_id = accounts.id
);
