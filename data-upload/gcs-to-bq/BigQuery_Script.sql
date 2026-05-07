-- TRUNCATE TABLE `your-project-id.demo_dataset.order_items`;
-- TRUNCATE TABLE `your-project-id.demo_dataset.orders`;
-- TRUNCATE TABLE `your-project-id.demo_dataset.customers`;
-- TRUNCATE TABLE `your-project-id.demo_dataset.products`;

CREATE TABLE `your-project-id.demo_dataset.customers`
	(
	  customer_id INT64,
	  name STRING,
	  email STRING,
	  region STRING,
	  signup_date DATE,
	  is_premium BOOL
	);
	CREATE TABLE `your-project-id.demo_dataset.products`
	(
	  product_id INT64,
	  product_name STRING,
	  category STRING,
	  unit_price FLOAT64,
	  stock_qty INT64
	);
	CREATE TABLE `your-project-id.demo_dataset.orders`
	(
	  order_id INT64,
	  customer_id INT64,
	  order_date DATE,
	  status STRING,
	  payment_method STRING,
	  total_amount FLOAT64
	);
	CREATE TABLE `your-project-id.demo_dataset.order_items`
	(
	  item_id INT64,
	  order_id INT64,
	  product_id INT64,
	  quantity INT64,
	  unit_price FLOAT64,
	  line_total FLOAT64
	);

SELECT 'customers' as Table_Name, COUNT(*) as Row_Count FROM `your-project-id.demo_dataset.customers`
UNION ALL
SELECT 'products' as Table_Name, COUNT(*) as Row_Count FROM `your-project-id.demo_dataset.products`
UNION ALL
SELECT 'orders' as Table_Name, COUNT(*) as Row_Count FROM `your-project-id.demo_dataset.orders`
UNION ALL
SELECT 'order_items' as Table_Name, COUNT(*) as Row_Count FROM `your-project-id.demo_dataset.order_items`;

--Create load_log table for audit purpose
CREATE TABLE `your-project-id.demo_dataset.load_log` (
  run_id        STRING,
  file_name     STRING,
  gcs_uri       STRING,
  table_name    STRING,
  status        STRING,       -- 'SUCCESS' | 'FAILED'
  rows_loaded   INT64,
  error_message STRING,
  started_at    TIMESTAMP,
  completed_at  TIMESTAMP,
  duration_sec  FLOAT64,
  triggered_by  STRING        -- the trigger file path
);

select * from `your-project-id.demo_dataset.load_log` limit 100;