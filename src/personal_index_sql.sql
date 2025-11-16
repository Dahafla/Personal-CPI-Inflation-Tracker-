-- Normalize CPI to base=100
DROP VIEW IF EXISTS cpi_norm;
CREATE VIEW cpi_norm AS
WITH base AS (
  SELECT c.month AS base_month, c.value AS base_val
  FROM cpi_series c
  ORDER BY c.month
  LIMIT 1
)
SELECT c.month,
       (c.value / base.base_val) * 100.0 AS cpi_index
FROM cpi_series c, base;

-- Personal CPI per user
DROP VIEW IF EXISTS personal_index;
CREATE VIEW personal_index AS
SELECT
  b.cc_num,
  n.month,
  ROUND(SUM(b.w0 * n.cpi_index), 2) AS personal_cpi
FROM cpi_norm n
JOIN base_weights b ON 1=1
GROUP BY b.cc_num, n.month
ORDER BY b.cc_num, n.month;
