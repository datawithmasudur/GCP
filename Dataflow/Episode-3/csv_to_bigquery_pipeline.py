import csv
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions


def parse_csv(line):
    # csv.reader handles quoted fields with commas inside them correctly,
    # unlike a simple line.split(',')
    reader = csv.reader([line])
    row = next(reader)

    (row_id, order_id, order_date, ship_date, ship_mode, customer_id,
     customer_name, segment, country, city, state, postal_code, region,
     product_id, category, sub_category, product_name, sales) = row

    return {
        'row_id': int(row_id),
        'order_id': order_id,
        'order_date': order_date,
        'ship_date': ship_date,
        'ship_mode': ship_mode,
        'customer_id': customer_id,
        'customer_name': customer_name,
        'segment': segment,
        'country': country,
        'city': city,
        'state': state,
        'postal_code': postal_code,
        'region': region,
        'product_id': product_id,
        'category': category,
        'sub_category': sub_category,
        'product_name': product_name,
        'sales': float(sales)
    }


def run():
    options = PipelineOptions(
        temp_location='gs://dataflow_demo_bucket/temp'
    )
    table_schema = (
        'row_id:INTEGER,order_id:STRING,order_date:STRING,ship_date:STRING,'
        'ship_mode:STRING,customer_id:STRING,customer_name:STRING,segment:STRING,'
        'country:STRING,city:STRING,state:STRING,postal_code:STRING,region:STRING,'
        'product_id:STRING,category:STRING,sub_category:STRING,'
        'product_name:STRING,sales:FLOAT'
    )

    with beam.Pipeline(options=options) as pipeline:
        (
            pipeline
            | 'Read CSV' >> beam.io.ReadFromText(
                'gs://dataflow_demo_bucket/sales_data.csv', skip_header_lines=1)
            | 'Parse CSV' >> beam.Map(parse_csv)
            | 'Write to BigQuery' >> beam.io.WriteToBigQuery(
                'upbeat-math-480123-r1:sales_dataset.sales_table',
                schema=table_schema,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED
            )
        )


if __name__ == '__main__':
    run()