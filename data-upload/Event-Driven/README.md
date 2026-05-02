# GCS File Watcher — Setup & Run Guide

## What files in the package

Three files. That's the whole project.

```
watcher.py          ← the watcher (watches folder, uploads to GCS, logs everything)
Dockerfile          ← wraps watcher.py into a container
requirements.txt    ← two Python packages
```

## How it works

```
C:\data\source\
  ├── customers.parquet   ← drop your data files
  ├── order_items.parquet
  ├── orders.parquet
  ├── products.parquet
  └── complete.txt    ← drop this LAST → upload fires instantly
```

The container watches `/app/source` (which is your `C:\data\source` folder).
The moment `complete.txt` appears, it uploads every other file to GCS,
logs the result, move source files to archive folder `C:\data\source\archive`
then deletes `complete.txt` so you're ready for the next batch.
On failure, remaining files stays in the folder and `complete.txt` stays — just drop it again to retry.

---

## Step 1 — GCP setup (one-time)

### Create a GCS bucket
1. Go to https://console.cloud.google.com/storage
2. Click **Create bucket** → give it a name → `upload_onprem_files`

### Create a service account
1. Go to https://console.cloud.google.com/iam-admin/serviceaccounts
2. **Create Service Account** → name it `storage-transfer-sa` → **Create and Continue**
3. Role: **Storage Object Creator** → **Done**
4. Click the account → **Keys** tab → **Add Key** → **JSON** → download
5. Save the file to `C:\key_files\storage-transfer-sa.json`

---

## Step 2 — Create your source and logs folders

```
mkdir C:\data\source
mkdir C:\data\logs
```

---

## Step 3 — Build the Docker image

Open a terminal in the folder where your three files live and run:

```bash
docker build -t gcs-watcher .
```

You only need to do this once (or again after editing watcher.py).

---

## Step 4 — Run the container

```bash
docker run -d `
  --name gcs-watcher `
  --restart unless-stopped `
  -e BUCKET_NAME=upload_onprem_files `
  -e GCS_PREFIX=landing `
  -v C:\data\source:/app/source `
  -v C:\data\logs:/app/logs `
  -v C:\key_files\storage-transfer-sa.json:/app/secrets/key.json:ro `
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/key.json `
  gcs-watcher
```

**Replace `upload_onprem_files`** with your actual GCS bucket name.
**Replace the paths** (`C:\data\...`, `C:\secrets\...`) with your actual Windows paths.

`-d` runs it in the background. `--restart unless-stopped` means it auto-starts
when Docker Desktop starts.

### Mac / Linux version of the same command
```bash
docker run -d \
  --name gcs-watcher \
  --restart unless-stopped \
  -e BUCKET_NAME=upload_onprem_files \
  -e GCS_PREFIX=landing \
  -v ~/data/source:/app/source \
  -v ~/data/logs:/app/logs \
  -v ~/.secrets/gcs-key.json:/app/secrets/key.json:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/key.json \
  gcs-watcher
```

---

## Step 5 — Confirm it's running

```bash
docker ps
```

You should see `gcs-watcher` in the list with status `Up`.

```bash
docker logs gcs-watcher
```

You should see:
```
2026-04-30 22:53:10  INFO      ==================================================
2026-04-30 22:53:10  INFO      GCS Watcher running
2026-04-30 22:53:10  INFO        Watching : /app/source
2026-04-30 22:53:10  INFO        Bucket   : gs://upload_onprem_files/landing
2026-04-30 22:53:10  INFO        Trigger  : drop complete.txt to upload
2026-04-30 22:53:10  INFO      ==================================================
```

---

## Step 6 — Trigger your first upload

Copy some files into the source folder, then drop complete.txt last:

```bash
# Windows
copy customers.parquet C:\data\source\
copy orders.parquet C:\data\source\
copy order_items.parquet C:\data\source\
copy products.parquet C:\data\source\
echo done > C:\data\source\complete.txt
```

Watch the logs fire in real time:
```bash
docker logs gcs-watcher -f
```

Expected output:
```
2026-04-30 22:53:59  INFO      ──────────────────────────────────────────────────
2026-04-30 22:53:59  INFO      Trigger detected: complete.txt
2026-04-30 22:53:59  INFO      Found 4 file(s) — starting upload...
2026-04-30 22:53:59  INFO        ✓  customers.parquet  →  gs://upload_onprem_files/landing/customers.parquet  (0.56s)
2026-04-30 22:53:59  INFO            ↳ archived to /app/source/archive/2026-04-30/customers.parquet
2026-04-30 22:54:00  INFO        ✓  orders.parquet  →  gs://upload_onprem_files/landing/orders.parquet  (0.23s)
2026-04-30 22:54:00  INFO            ↳ archived to /app/source/archive/2026-04-30/orders.parquet
2026-04-30 22:54:00  INFO        ✓  order_items.parquet  →  gs://upload_onprem_files/landing/order_items.parquet  (0.22s)
2026-04-30 22:54:00  INFO            ↳ archived to /app/source/archive/2026-04-30/order_items.parquet
2026-04-30 22:54:00  INFO        ✓  products.parquet  →  gs://upload_onprem_files/landing/products.parquet  (0.22s)
2026-04-30 22:54:00  INFO            ↳ archived to /app/source/archive/2026-04-30/products.parquet
2026-04-30 22:54:00  INFO      All uploads done. Waiting for next batch...
2026-04-30 22:54:00  INFO      ──────────────────────────────────────────────────
```

Then go to https://console.cloud.google.com/storage and confirm the files are there.

---

## Checking the log file

Logs are written both to the console and to `C:\data\logs\upload_log.txt`.
Open it in Notepad any time — it's a plain text file.

```bash
# Live tail from terminal:
docker logs gcs-watcher -f

# Read the file directly (Windows PowerShell):
Get-Content C:\data\logs\upload_log.txt -Wait
```

---

## Testing scenarios

### Normal upload
```bash
copy report.csv C:\data\source\
echo. > C:\data\source\complete.txt
# Expected: file appears in GCS Console
```

### Retry after failure
```bash
# Stop the container to simulate a network error
docker stop gcs-watcher

# Drop files while it's stopped (they'll sit there)
copy data.csv C:\data\source\
echo. > C:\data\source\complete.txt

# Start it again
docker start gcs-watcher

# Watch logs — it won't re-detect the already-existing complete.txt
# (watchdog only fires on NEW file creation)
# Solution: delete and re-drop complete.txt:
del C:\data\source\complete.txt
echo. > C:\data\source\complete.txt
# Expected: upload succeeds now
```

### Test from inside the container
```bash
# Open a shell inside the running container
docker exec -it gcs-watcher bash

# Drop a trigger from inside
echo "" > /app/source/complete.txt

# Run the upload function directly (bypasses watchdog)
python -c "import watcher; watcher.upload_files()"

# Check logs
cat /app/logs/upload_log.txt

# Exit
exit
```

### Confirm credentials work
```bash
docker exec gcs-watcher python -c "
from google.cloud import storage
c = storage.Client()
print('Connected. Project:', c.project)
"
```

---

## Stop / start / remove

```bash
# Stop (keeps container, can restart)
docker stop gcs-watcher

# Start again
docker start gcs-watcher

# View logs
docker logs gcs-watcher -f

# Remove container completely
docker stop gcs-watcher
docker rm gcs-watcher

# Remove image (if you want to start fresh)
docker rmi gcs-watcher
```

---

## Rebuild after code changes

```bash
docker stop gcs-watcher
docker rm gcs-watcher
docker build -t gcs-watcher .
docker run -d --name gcs-watcher --restart unless-stopped \
  -e BUCKET_NAME=upload_onprem_files \
  -e GCS_PREFIX=landing \
  -v C:\data\source:/app/source \
  -v C:\data\logs:/app/logs \
  -v C:\secrets\gcs-key.json:/app/secrets/key.json:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/key.json \
  gcs-watcher
```

---

## Troubleshooting

| Error in logs | Cause | Fix |
|---|---|---|
| `DefaultCredentialsError` | Key file not found or path wrong | Check `-v` path to key.json in docker run |
| `403 Forbidden` | Wrong IAM role | Service account needs **Storage Object Creator** |
| `404 Not Found` | Wrong bucket name | Check `-e BUCKET_NAME=` in docker run |
| Files not uploading | complete.txt dropped before data files | Drop data files first, complete.txt last |
| Container not in `docker ps` | It crashed | Run `docker logs gcs-watcher` to see the error |