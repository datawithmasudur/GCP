import json
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions


def parse_message(message):
    return json.loads(message.decode('utf-8'))


def run():
    options = PipelineOptions(
        streaming=True,
        temp_location='gs://dataflow_demo_bucket/temp'
        )
    table_schema = 'product:STRING,sales:FLOAT'

    with beam.Pipeline(options=options) as pipeline:
        (
            pipeline
            | 'Read from PubSub' >> beam.io.ReadFromPubSub(
                subscription='projects/upbeat-math-480123-r1/subscriptions/sales-events-sub')
            | 'Parse JSON' >> beam.Map(parse_message)
            | 'Write to BigQuery' >> beam.io.WriteToBigQuery(
                'upbeat-math-480123-r1:sales_dataset.streaming_sales',
                schema=table_schema,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
                method=beam.io.WriteToBigQuery.Method.STREAMING_INSERTS
            )
        )


if __name__ == '__main__':
    run()
