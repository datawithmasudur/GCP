import functions_framework
import concurrent.futures
import uuid
from datetime import datetime, timezone
from google.cloud import bigquery, storage

PROJECT_ID   = "your-project-id"
DATASET_ID   = "demo_dataset"
BUCKET_NAME  = "upload_onprem_files"
LANDING_PATH = "landing/"
ARCHIVE_BASE = "archive/"

FILE_TABLE_MAP = {
    "customers.parquet":   "customers",
    "orders.parquet":      "orders",
    "order_items.parquet": "order_items",
    "products.parquet":    "products",
}

TRIGGER_FILE = "landing/complete.txt"
LOG_TABLE    = f"{PROJECT_ID}.{DATASET_ID}.load_log"


def now_utc():
    return datetime.now(timezone.utc)


def load_parquet_to_bq(gcs_uri: str, table_id: str, run_id: str, trigger_file: str) -> dict:
    """
    Submit a single BQ load job and wait for completion.
    Returns a log record dict regardless of success or failure.
    """
    bq_client  = bigquery.Client()
    table_ref  = f"{PROJECT_ID}.{DATASET_ID}.{table_id}"
    started_at = now_utc()

    log = {
        "run_id":       run_id,
        "file_name":    gcs_uri.split("/")[-1],
        "gcs_uri":      gcs_uri,
        "table_name":   table_id,
        "started_at":   started_at.isoformat(),
        "triggered_by": trigger_file,
        # filled in below
        "status":        None,
        "rows_loaded":   None,
        "error_message": None,
        "completed_at":  None,
        "duration_sec":  None,
    }

    try:
        print(f"  Loading {gcs_uri} → {table_ref}")
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        job = bq_client.load_table_from_uri(gcs_uri, table_ref, job_config=job_config)
        job.result()

        completed_at = now_utc()
        log.update({
            "status":       "SUCCESS",
            "rows_loaded":  job.output_rows,
            "completed_at": completed_at.isoformat(),
            "duration_sec": round((completed_at - started_at).total_seconds(), 2),
        })
        print(f"  Done: {job.output_rows} rows → {table_ref}")

    except Exception as e:
        completed_at = now_utc()
        log.update({
            "status":        "FAILED",
            "rows_loaded":   0,
            "error_message": str(e),
            "completed_at":  completed_at.isoformat(),
            "duration_sec":  round((completed_at - started_at).total_seconds(), 2),
        })
        print(f"  ERROR loading {table_id}: {e}")

    return log


def write_load_logs(bq_client: bigquery.Client, log_rows: list[dict]):
    """Insert all log rows into load_log in one call."""
    errors = bq_client.insert_rows_json(LOG_TABLE, log_rows)
    if errors:
        # Non-fatal: don't let logging failure kill the pipeline
        print(f"  WARNING: Failed to write some log rows: {errors}")
    else:
        print(f"  Logged {len(log_rows)} rows to {LOG_TABLE}")


def archive_files(storage_client, all_files: list[str], dated_folder: str):
    """Copy each file to archive/YYYY-MM-DD/ then delete the source."""
    bucket = storage_client.bucket(BUCKET_NAME)
    for blob_name in all_files:
        src_blob  = bucket.blob(blob_name)
        filename  = blob_name.split("/")[-1]
        dest_name = f"{ARCHIVE_BASE}{dated_folder}/{filename}"
        bucket.copy_blob(src_blob, bucket, dest_name)
        src_blob.delete()
        print(f"  Archived: {blob_name} → {dest_name}")


@functions_framework.cloud_event
def gcs_to_bigquery(cloud_event):
    data      = cloud_event.data
    file_name = data["name"]

    # FIX 1: Exact match only
    if file_name != TRIGGER_FILE:
        print(f"Ignoring file: {file_name}")
        return

    # FIX 2: Idempotency guard — skip duplicate events
    storage_client = storage.Client()
    trigger_blob   = storage_client.bucket(BUCKET_NAME).blob(TRIGGER_FILE)
    if not trigger_blob.exists():
        print(f"Trigger file already removed — duplicate event, skipping.")
        return

    print(f"Trigger file detected: {file_name} — starting pipeline")

    run_id = str(uuid.uuid4())   # Unique ID ties all log rows for this run together
    today  = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    load_tasks      = []
    files_to_archive = [file_name]

    for parquet_file, table_name in FILE_TABLE_MAP.items():
        gcs_uri = f"gs://{BUCKET_NAME}/{LANDING_PATH}{parquet_file}"
        load_tasks.append((gcs_uri, table_name))
        files_to_archive.append(f"{LANDING_PATH}{parquet_file}")

    # Run all BQ load jobs in parallel, collecting logs from each
    log_rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(load_parquet_to_bq, uri, tbl, run_id, file_name): tbl
            for uri, tbl in load_tasks
        }
        for future in concurrent.futures.as_completed(futures):
            log_rows.append(future.result())

    # Write all logs to BigQuery (win or lose)
    bq_client = bigquery.Client()
    write_load_logs(bq_client, log_rows)

    # Check for any failures after logging
    failed = [r for r in log_rows if r["status"] == "FAILED"]
    if failed:
        names = [r["table_name"] for r in failed]
        raise RuntimeError(f"Load failures (files NOT archived): {names}")

    print(f"All loads complete. Archiving to {ARCHIVE_BASE}{today}/")
    archive_files(storage_client, files_to_archive, today)
    print("Pipeline complete.")