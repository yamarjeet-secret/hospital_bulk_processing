# hospital_bulk_processing

This FastAPI application provides endpoints for bulk uploading, validating, and activating hospitals using CSV files. It uses concurrent processing to handle multiple hospital records efficiently.

---

## Features

- **CSV Validation**: Ensures uploaded CSV files are valid and have the correct headers.
- **Bulk Hospital Creation**: Creates multiple hospitals in parallel using a batch ID.
- **Batch Activation**: Activates all hospitals in a batch if all were successfully created.
- **Retry Mechanism**: Retries failed HTTP requests with exponential backoff.

---

## Requirements

- Python 3.11+
- FastAPI
- Requests
- Uvicorn
- Python-Multipart
- Pydantic

Optional for testing:

- `pytest`  
- `httpx`

---

---

## Importatnt links
1. Github repo link : **https://github.com/yamarjeet-secret/hospital_bulk_processing.git**
2. Base Render Url for bulk processing: **https://hospital-bulk-processing.onrender.com/docs#/**


## Installation

1. Acess through Render: https://hospital-bulk-processing.onrender.com/docs#/
   
2. Clone the repository:

```bash
git clone https://github.com/yamarjeet-secret/hospital_bulk_processing.git
cd hospital_bulk_processing

3. How to Run Locally
  a. Install dependencies: pip install -r requirements.txt
  b. Run the FastAPI server with Uvicorn: uvicorn hospital_bulk_processing:app --reload
  c. Open your browser at: http://localhost:8000/docs#/

4. Run using docker
  a. Build Docker Image: docker build -t hospital-bulk-api .
  b. Run Docker Container: docker run -d -p 8000:8000 hospital-bulk-api:latest
  c. Access at : http://localhost:8000/docs#/

'''

## Run Testcase Command
python3 test_integeration.py
python3 -m pytest test_unit.py -v


 ---

