-- TRUNCATE TABLE `upbeat-math-480123-r1.demo_dataset.customers`;

CREATE TABLE `upbeat-math-480123-r1.demo_dataset.customers`
	(
	  customer_id INT64,
	  name STRING,
	  email STRING,
	  region STRING,
	  signup_date DATE,
	  is_premium BOOL
	);

SELECT * FROM `upbeat-math-480123-r1.demo_dataset.customers`;
