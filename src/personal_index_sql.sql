-- Normalize CPI to base=100
DROP VIEW IF EXISTS cpi_norm;
CREATE VIEW cpi_norm AS
WITH base AS
(
  SELECT
    category,
    MIN(month) AS base_month
    FROM cpi_series
    GROUP BY category
),

base_val AS (
  SELECT
    c.category,
    c.month AS base_month,
    c.value AS base_val
  FROM cpi_series c
  JOIN base b
    ON c.category = b.category
    AND c.month = b.base_month
)
SELECT 
  c.category,
  strftime('%Y-%m', c.month) AS ym,
  (c.value / bv.base_val) * 100.0 AS cpi_index
FROM cpi_series c
JOIN base_val bv
  ON c.category = bv.category;

-- Personal CPI per user
-- Personal CPI per user based on their own monthly spend

DROP VIEW IF EXISTS personal_index;
CREATE VIEW personal_index AS
WITH user_months AS (
  SELECT DISTINCT
    cc_num,
    month AS ym
  FROM monthly_weights
)
SELECT
  u.cc_num,
  DATE(u.ym || '-01') AS month,
  ROUND(SUM(b.w0 * n.cpi_index), 2) AS personal_cpi
FROM user_months u
JOIN base_weights b
  ON u.cc_num   = b.cc_num
JOIN cpi_norm n
  ON n.category = b.category
 AND n.ym       = u.ym
GROUP BY u.cc_num, month
ORDER BY u.cc_num, month;
