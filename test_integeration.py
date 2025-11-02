from fastapi.testclient import TestClient
from hospital_bulk_processing import app
import io

client = TestClient(app)

def test_csv_validation_endpoint():
    csv_content = "name,address,phone\nA,B,123"
    response = client.post(
        "/hospitals/csv_validate",
        files={"file": ("test.csv", csv_content, "text/csv")}
    )
    assert response.status_code == 200

def test_bulk_upload_success(monkeypatch):
    # Mock dependent functions to simulate successful processing
    def mock_bulk_processing(upload_file):
        return {
            "batch_id": "uuid123",
            "total_hospitals": 2,
            "processed_hospitals": 2,
            "failed_hospitals": 0,
            "processing_time_seconds": 10,
            "batch_activated": True,
            "hospitals": [
                {"row": 1, "hospital_id": 1, "name": "A", "status": "created_and_activated"}
            ]
        }

    monkeypatch.setattr("hospital_bulk_processing.bulk_processing", mock_bulk_processing)

    csv_content = "name,address,phone\nA,B,123"
    response = client.post(
        "/hospitals/bulk",
        files={"file": ("test.csv", csv_content, "text/csv")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["batch_activated"] is True
    assert data["total_hospitals"] == 2
