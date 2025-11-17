
/*
- transforms raw transactions data into a structure, CPI aligned format
-Semantic layer that enables accurate aggregation and weight calculations
*/


DROP TABLE IF EXISTS transactions;
CREATE TABLE transactions AS
SELECT
date,
cc_num,

CASE
    WHEN category IN ('grocery_net', 'grocery_pos')
        THEN 'Groceries'
    WHEN category = 'gas_transport'
        THEN 'Gas & Transport'
    WHEN category = 'food_dining'
        THEN 'Restaurants & Dining'
    WHEN category = 'entertainment'
        THEN 'Entertainment'
    WHEN category IN ('shopping_net', 'shopping_pos')
        THEN 'Shopping'
    WHEN category = 'health_fitness'
        THEN 'Health & Fitness'
    WHEN category = 'home'
        THEN 'Home'
    WHEN category = 'kids_pets'
        THEN 'Kids & Pets'
    WHEN category = 'personal_care'
        THEN 'Personal Care'
    WHEN category = 'travel'
        THEN 'Travel'
    WHEN category IN ('misc_net', 'misc_pos')
        THEN 'Miscellaneous'
END AS category,

amt AS spend

FROM transactions_raw
WHERE amt > 0;

