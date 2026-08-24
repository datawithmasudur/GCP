import json
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.transforms.window import FixedWindows


def parse_message(message):
    return json.loads(message.decode('utf-8'))

def to_keyed_sales(event):
    # Key all events the same way, so they group together within a window
    return ('all_sales', event['sales'])

def run():
    options = PipelineOptions(
        streaming=True,
        temp_location='gs://dataflow_demo_bucket/temp'
        )
    table_schema = 'window_end:STRING,total_sales:FLOAT'

    with beam.Pipeline(options=options) as pipeline:
        (
            pipeline
            | 'Read from PubSub' >> beam.io.ReadFromPubSub(
                subscription='projects/upbeat-math-480123-r1/subscriptions/sales-events-sub')
            | 'Parse JSON' >> beam.Map(parse_message)
            | 'Add Window' >> beam.WindowInto(FixedWindows(60))
            | 'Key by All' >> beam.Map(to_keyed_sales)
            | 'Sum per Window' >> beam.CombinePerKey(sum)
            | 'Format for BigQuery' >> beam.Map(
                lambda kv: {'window_end': 'see_console', 'total_sales': kv[1]})
            | 'Write to BigQuery' >> beam.io.WriteToBigQuery(
                'upbeat-math-480123-r1:sales_dataset.windowed_sales',
                schema=table_schema,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
                method=beam.io.WriteToBigQuery.Method.STREAMING_INSERTS
            )
        )


if __name__ == '__main__':
    run()
