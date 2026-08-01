import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions

def run():
    options = PipelineOptions()

    with beam.Pipeline(options=options) as pipeline:
        (
            pipeline
            | 'Read Input' >> beam.io.ReadFromText('gs://dataflow_demo_bucket/input.txt')
            | 'Uppercase Line' >> beam.Map(lambda line: line.upper())
            | 'Write Output' >> beam.io.WriteToText('gs://dataflow_demo_bucket/output/output')
        )

if __name__ == '__main__':
    run()