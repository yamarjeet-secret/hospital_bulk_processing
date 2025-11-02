from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import time
import uuid
import csv
import io
import requests
import logging 
from concurrent.futures import ThreadPoolExecutor, as_completed


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
app = FastAPI(title="Bulk Hospital Upload API")

MAX_RETRIES = 3
MAX_ROWS = 20
BASE_DELAY = 1
MAX_WORKERS = 20
BASE_URL = "https://hospital-directory.onrender.com"
CREATE_HOSPITAL_URL =f"{BASE_URL}/hospitals/"
GET_BY_BATCH_URL = BASE_URL + "/hospitals/batch/{batch_id}"
ACTIVATE_BATCH_URL = BASE_URL + "/hospitals/batch/{batch_id}/activate"


def validate_csv_file(upload_file: UploadFile):
    """Ensure it's a CSV and has correct headers."""
    if not upload_file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be a .csv")
    content = upload_file.file.read().decode("utf-8")
    upload_file.file.seek(0)  # reset pointer for re-reading later

    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    if len(rows) > MAX_ROWS:
        raise HTTPException(status_code=400, detail=f"CSV file has more than {MAX_ROWS} data rows ({len(rows)})")

    return content  # return content for re-use

def generate_unique_batchid():
    """Generate a unique UUID for this batch."""
    return str(uuid.uuid4())


def process_single_hospital(row, row_number, batch_id):
    """Handles creation of a single hospital with retry & backoff."""
    name = row.get("name")
    address = row.get("address")
    phone = row.get("phone", None)

    if not name or not address:
        return {"row": row_number, "status": "failed", "reason": "Missing required name or address"}

    payload = {
        "name": name,
        "address": address,
        "phone": phone,
        "creation_batch_id": batch_id
    }

    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            response = requests.post(CREATE_HOSPITAL_URL, json=payload, timeout=10)
            data = response.json()
            logger.info(f"attempt and data {attempt} and {data}")
            if response.status_code == 200:
                return {
                    "row": row_number,
                    "hospital_id": data.get("id"),
                    "name": data.get("name"),
                    "status": "created"
                }
            else:
                attempt += 1
                if attempt < MAX_RETRIES:
                    delay = BASE_DELAY * (2 ** (attempt - 1))
                    time.sleep(delay)
                else:
                    return {"row": row_number, "status": "failed", "reason": f"HTTP {response.status_code}"}
        except Exception as e:
            attempt += 1
            if attempt < MAX_RETRIES:
                delay = BASE_DELAY * (2 ** (attempt - 1))
                time.sleep(delay)
            else:
                return {"row": row_number, "status": "failed", "reason": str(e)}



def create_hospitals_from_csv(csv_content: str, batch_id: str, resume_state=None):
    """Read CSV, make POST /hospitals calls, and collect results."""
    reader = csv.DictReader(io.StringIO(csv_content))
    results = resume_state if resume_state else []

    # Identify rows that still need processing
    pending_rows = []
    for i, row in enumerate(reader, start=1):
        already_done = resume_state and any(r["row"] == i and r["status"] == "created" for r in resume_state)
        if not already_done:
            pending_rows.append((i, row))

    logger.info(f"Total pending rows to process: {len(pending_rows)}")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(
                process_single_hospital, row, row_number, batch_id
            ): row_number
            for row_number, row in pending_rows
        }

        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({"row": futures[future], "status": "failed", "reason": str(e)})

    return results

def activate_hospitals_by_batch_id(batch_id: str):
    """Activate all hospitals under a specific batch ID."""
    try:
        url = ACTIVATE_BATCH_URL.format(batch_id=batch_id)
        resp = requests.patch(url, timeout=10)

        if resp.status_code in (200, 204):
            return {"batch_id": batch_id, "status": "activated"}
        else:
            logger.info(f"not able to activated with batch id {batch_id}")
            return {
                "batch_id": batch_id,
                "status": "failed",
                "error": f"Activation failed with HTTP {resp.status_code}"
            }
    except Exception as e:
        return {"batch_id": batch_id, "status": "failed", "error": str(e)}


def get_hospital_details_by_batch_id(batch_id: str):
    """Fetch hospitals created in this batch (using existing endpoint)."""
    try:
        resp = requests.get(GET_BY_BATCH_URL.format(batch_id=batch_id), timeout=1000)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"Failed to fetch hospitals for batch {batch_id}", "status": resp.status_code}
    except Exception as e:
        return {"error": str(e)}


def bulk_processing(upload_file: UploadFile):
    """Main workflow that ties everything together."""
    start_time = time.time()
    # Step 1: Validate CSV
    csv_content = validate_csv_file(upload_file)

    # Step 2: Generate batch ID
    batch_id = generate_unique_batchid()
    # Step 3: Create hospitals
    results = create_hospitals_from_csv(csv_content, batch_id)
    # Step 4: If all successful, activate the batch
    success_count = sum(1 for r in results if r["status"] == "created")
    total_records = len(results)

    batch_status = False
    if success_count == total_records:
        res = activate_hospitals_by_batch_id(batch_id)
        if res.get('status') == "activated":
            batch_status = True

    # Step 5: Get batch details (optional)
    # batch_details = get_hospital_details_by_batch_id(batch_id)
    hospitals_summary = []
    for idx, hospital in enumerate(results, start=1):
        hospital_id = hospital.get("hospital_id")
        status = "created_and_activated" if batch_status else hospital.get("status")
        hospitals_summary.append({
            "row": idx,
            "hospital_id": hospital_id,
            "name": hospital.get("name"),
            "status": status
        })
    end_time = time.time()
    processing_time_seconds = int(end_time - start_time)
    # Return summary
    return {
        "batch_id": batch_id,
        "total_hospitals": total_records,
        "processed_hospitals": success_count,
        "failed_hospitals": total_records - success_count,
        "processing_time_seconds": processing_time_seconds,
        "batch_activated": batch_status,
        "hospitals": hospitals_summary
    }



@app.post("/hospitals/bulk")
def upload_bulk_hospitals(file: UploadFile = File(...)):
    result = bulk_processing(file)
    return JSONResponse(result)


@app.post("/hospitals/csv_validate")
def csv_validation(file: UploadFile = File(...)):
    try:
        result = validate_csv_file(file)
    except Exception as e:
        return {"error": str(e)}
    return result

