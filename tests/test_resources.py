from datetime import datetime, timedelta

from fastapi.testclient import TestClient


def test_create_and_list_resources(client: TestClient):
    payload = {
        "title": "FastAPI Course",
        "resource_type": "course",
        "provider": "Udemy",
        "url": "https://example.com",
        "total_units": 20,
        "tags": ["backend", "python"],
        "target_skills": ["fastapi", "rest-api"],
    }

    create_res = client.post("/resources", json=payload)
    assert create_res.status_code == 200
    data = create_res.json()
    assert data["title"] == "FastAPI Course"
    assert data["status"] == "not_started"

    list_res = client.get("/resources")
    assert list_res.status_code == 200
    all_resources = list_res.json()
    assert any(r["title"] == "FastAPI Course" for r in all_resources)

def test_update_resource_progress(client: TestClient):
    # create a resource with total_units
    payload = {
        "title": "Algorithms Book",
        "resource_type": "book",
        "provider": "Book",
        "total_units": 10,
        "tags": ["algorithms"],
        "target_skills": ["algorithms"],
    }
    create_res = client.post("/resources", json=payload)
    assert create_res.status_code == 200
    resource_id = create_res.json()["id"]

    # update progress to 5/10
    update_payload = {"completed_units": 5}
    patch_res = client.patch(f"/resources/{resource_id}", json=update_payload)
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["completed_units"] == 5
    assert updated["progress_percent"] == 50.0


def test_stats_overview_counts_time_and_resources(client: TestClient):
    # create resource
    payload = {
        "title": "FastAPI Course",
        "resource_type": "course",
        "provider": "Udemy",
        "total_units": 20,
        "tags": ["backend"],
        "target_skills": ["fastapi"],
    }
    create_res = client.post("/resources", json=payload)
    resource_id = create_res.json()["id"]

    # log 1 hour study session
    start = datetime.utcnow()
    end = start + timedelta(hours=1)
    session_payload = {
        "resource_id": resource_id,
        "started_at": start.isoformat(),
        "ended_at": end.isoformat(),
        "notes": "Watched first few lessons",
    }
    session_res = client.post("/sessions", json=session_payload)
    assert session_res.status_code == 200

    # check stats
    stats_res = client.get("/stats/overview")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_resources"] >= 1
    assert stats["total_study_hours"] >= 1.0