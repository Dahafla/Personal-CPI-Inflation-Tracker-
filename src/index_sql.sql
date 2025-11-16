DROP VIEW IF EXISTS monthly_weights;
CREATE VIEW monthly_weights AS
SELECT
cc_num,
strftime('%Y-%m', date) AS month,
category,
SUM(spend) AS spend,
SUM(SUM(spend)) OVER (PARTITION BY cc_num, strftime('%Y-%m', date)) AS total_month, 
SUM(spend)*1.0 / SUM(SUM(spend)) OVER (PARTITION BY cc_num, strftime('%Y-%m', date)) AS weight

FROM transactions
GROUP BY cc_num, month, category;

-- 3.2 Base month per user
DROP VIEW IF EXISTS base_month;
CREATE VIEW base_month AS
SELECT cc_num, MIN(month) AS month
FROM monthly_weights
GROUP BY cc_num;

-- 3.3 Base weights per user
DROP VIEW IF EXISTS base_weights;
CREATE VIEW base_weights AS
SELECT mw.cc_num, mw.category, mw.weight AS w0
FROM monthly_weights mw
JOIN base_month b ON mw.cc_num = b.cc_num AND mw.month = b.month;