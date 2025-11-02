import io
import csv
import pytest
import uuid
from fastapi import UploadFile
from hospital_bulk_processing import (
    validate_csv_file,
    generate_unique_batchid,
    process_single_hospital,
    create_hospitals_from_csv
)

class DummyUploadFile:
    def __init__(self, filename, content):
        self.filename = filename
        self.file = io.BytesIO(content.encode('utf-8'))

def test_validate_csv_file_valid():
    content = "name,address,phone\nA,B,12345"
    file = DummyUploadFile("test.csv", content)
    result = validate_csv_file(file)
    assert "A,B,12345" in result

def test_validate_csv_file_invalid_extension():
    file = DummyUploadFile("test.txt", "name,address,phone\nA,B,12345")
    with pytest.raises(Exception):
        validate_csv_file(file)

def test_generate_unique_batchid_is_uuid():
    batch_id = generate_unique_batchid()
    uuid_obj = uuid.UUID(batch_id)  # will raise if not valid
    assert isinstance(batch_id, str)

def test_process_single_hospital_missing_required_fields():
    row = {"name": "", "address": ""}
    result = process_single_hospital(row, 1, "uuid")
    assert result["status"] == "failed"
    assert "Missing required" in result["reason"]

def test_create_hospitals_from_csv_structure(monkeypatch):
    csv_data = "name,address,phone\nH1,Addr1,111\nH2,Addr2,222"
    batch_id = "uuid123"

    def mock_process_single(row, num, batch):
        return {"row": num, "status": "created", "hospital_id": num}

    monkeypatch.setattr("hospital_bulk_processing.process_single_hospital", mock_process_single)

    results = create_hospitals_from_csv(csv_data, batch_id)
    assert len(results) == 2
    assert all(r["status"] == "created" for r in results)
