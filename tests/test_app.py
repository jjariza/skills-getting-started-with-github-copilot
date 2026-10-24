import copy
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


@pytest.fixture(autouse=True)
def restore_activities():
    original_activities = copy.deepcopy(activities)
    yield
    activities.clear()
    activities.update(original_activities)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_root_redirects_to_frontend(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_data_without_cache(client):
    response = client.get("/activities")

    assert response.status_code == 200
    assert "Tennis Club" in response.json()
    assert response.headers["cache-control"] == "no-store"


def test_signup_adds_participant_and_is_visible_in_activity_list(client):
    activity_name = "Tennis Club"
    email = "new-student@mergington.edu"
    signup = client.post(
        f"/activities/{quote(activity_name, safe='')}/signup",
        params={"email": email},
    )

    assert signup.status_code == 200
    assert signup.json() == {"message": f"Signed up {email} for {activity_name}"}

    activities_response = client.get("/activities")
    assert email in activities_response.json()[activity_name]["participants"]


def test_duplicate_signup_is_rejected_without_adding_participant_twice(client):
    activity_name = "Tennis Club"
    email = "new-student@mergington.edu"
    activity_path = f"/activities/{quote(activity_name, safe='')}/signup"

    assert client.post(activity_path, params={"email": email}).status_code == 200
    duplicate = client.post(activity_path, params={"email": email})

    assert duplicate.status_code == 400
    assert activities[activity_name]["participants"].count(email) == 1


def test_signup_for_unknown_activity_returns_not_found(client):
    response = client.post(
        "/activities/Unknown%20Club/signup",
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_removes_participant_and_updates_activity_list(client):
    activity_name = "Tennis Club"
    email = "student-to-remove@mergington.edu"
    activity_path = f"/activities/{quote(activity_name, safe='')}/signup"
    assert client.post(activity_path, params={"email": email}).status_code == 200

    response = client.delete(activity_path, params={"email": email})

    assert response.status_code == 200
    assert response.json() == {"message": f"Unregistered {email} from {activity_name}"}
    assert email not in client.get("/activities").json()[activity_name]["participants"]


def test_unregister_missing_participant_returns_not_found(client):
    response = client.delete(
        "/activities/Tennis%20Club/signup",
        params={"email": "not-signed-up@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"


def test_unregister_from_unknown_activity_returns_not_found(client):
    response = client.delete(
        "/activities/Unknown%20Club/signup",
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"