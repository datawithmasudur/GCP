"""
watcher.py
──────────
Watches a folder. When complete.txt appears → uploads everything to GCS.
Logs every action to console and upload_log.txt.
"""

import os
import time
import logging
from pathlib import Path
# from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver
from google.cloud import storage

# ── CONFIG (edit these 2 lines) ──────────────────────────────────────────────
BUCKET_NAME  = os.environ.get("BUCKET_NAME", "your-bucket-name")
GCS_PREFIX   = os.environ.get("GCS_PREFIX",  "uploads")
# ─────────────────────────────────────────────────────────────────────────────

SOURCE_FOLDER = "/app/source"
TRIGGER_FILE  = "complete.txt"

# ── LOGGING: console + file ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/app/logs/upload_log.txt"),
    ],
)
log = logging.getLogger(__name__)


def upload_files():
    """Upload every file in SOURCE_FOLDER (except complete.txt) to GCS."""
    files = [
        f for f in Path(SOURCE_FOLDER).iterdir()
        if f.is_file() and f.name != TRIGGER_FILE
    ]

    if not files:
        log.warning("No files to upload — source folder is empty.")
        return True

    log.info(f"Found {len(files)} file(s) — starting upload...")
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    all_ok = True

    # Create archive folder based on today's date
    today_str = time.strftime("%Y-%m-%d")
    archive_dir = Path(SOURCE_FOLDER) / "archive" / today_str
    archive_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        blob_name = f"{GCS_PREFIX}/{f.name}"
        try:
            start = time.time()
            bucket.blob(blob_name).upload_from_filename(str(f))
            secs = round(time.time() - start, 2)

            log.info(f"  ✓  {f.name}  →  gs://{BUCKET_NAME}/{blob_name}  ({secs}s)")

            # Move file to archive after success
            dest = archive_dir / f.name

            # Handle duplicate file names
            if dest.exists():
                timestamp = time.strftime("%H%M%S")
                dest = archive_dir / f"{f.stem}_{timestamp}{f.suffix}"

            f.rename(dest)
            log.info(f"      ↳ archived to {dest}")

        except Exception as e:
            log.error(f"  ✗  {f.name}  FAILED: {e}")
            all_ok = False

    return all_ok


class WatchHandler(FileSystemEventHandler):

    def process_trigger(self, path):
        if Path(path).name != TRIGGER_FILE:
            return

        log.info("─" * 50)
        log.info(f"Trigger detected: {TRIGGER_FILE}")

        if upload_files():
            Path(path).unlink()
            log.info("All uploads done. Waiting for next batch...")
        else:
            log.error("Some uploads failed. Fix errors then drop complete.txt again.")
        log.info("─" * 50)

    def on_created(self, event):
        if not event.is_directory:
            self.process_trigger(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.process_trigger(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self.process_trigger(event.dest_path)


if __name__ == "__main__":
    Path("/app/logs").mkdir(parents=True, exist_ok=True)

    log.info("=" * 50)
    log.info("GCS Watcher running")
    log.info(f"  Watching : {SOURCE_FOLDER}")
    log.info(f"  Bucket   : gs://{BUCKET_NAME}/{GCS_PREFIX}")
    log.info(f"  Trigger  : drop {TRIGGER_FILE} to upload")
    log.info("=" * 50)

    # observer = Observer()
    observer = PollingObserver()
    observer.schedule(WatchHandler(), path=SOURCE_FOLDER, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    log.info("Watcher stopped.")