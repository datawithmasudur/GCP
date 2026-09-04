import json
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam import pvalue

GOOD_TAG = 'good'
BAD_TAG = 'bad'


class ParseMessage(beam.DoFn):
    def process(self, message):
        try:
            data = json.loads(message.decode('utf-8'))

            # basic validation: make sure required fields exist
            if 'product' not in data or 'sales' not in data:
                raise ValueError('Missing required field')

            yield pvalue.TaggedOutput(GOOD_TAG, data)

        except Exception as e:
            error_record = {
                'raw_message': message.decode('utf-8', errors='replace'),
                'error': str(e)
            }
            yield pvalue.TaggedOutput(BAD_TAG, error_record)


def run():
    options = PipelineOptions(
            streaming=True,
            temp_location='gs://dataflow_demo_bucket/temp'
            )

    good_schema = 'product:STRING,sales:FLOAT'
    bad_schema = 'raw_message:STRING,error:STRING'

    with beam.Pipeline(options=options) as pipeline:

        results = (
            pipeline
            | 'Read from PubSub' >> beam.io.ReadFromPubSub(
                subscription='projects/upbeat-math-480123-r1/subscriptions/sales-events-sub')
            | 'Parse and Validate' >> beam.ParDo(ParseMessage()).with_outputs(
                GOOD_TAG, BAD_TAG)
        )

        good_data = results[GOOD_TAG]
        bad_data = results[BAD_TAG]

        (
            good_data
            | 'Write Good to BigQuery' >> beam.io.WriteToBigQuery(
                'upbeat-math-480123-r1:sales_dataset.streaming_sales',
                schema=good_schema,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
                method=beam.io.WriteToBigQuery.Method.STREAMING_INSERTS
            )
        )

        (
            bad_data
            | 'Write Bad to Dead Letter Table' >> beam.io.WriteToBigQuery(
                'upbeat-math-480123-r1:sales_dataset.sales_dead_letter',
                schema=bad_schema,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
                method=beam.io.WriteToBigQuery.Method.STREAMING_INSERTS
            )
        )


if __name__ == '__main__':
    run()