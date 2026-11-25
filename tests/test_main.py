import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield

    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def register_user(username, email, password="SecurePass123"):
    response = client.post(
        "/register",
        json={
            "username": username,
            "email": email,
            "password": password
        }
    )

    assert response.status_code == 201

    return response.json()


def login_user(username, password="SecurePass123"):
    response = client.post(
        "/login",
        json={
            "username": username,
            "password": password
        }
    )

    assert response.status_code == 200

    return response.json()["access_token"]


def auth_headers(token):
    return {
        "Authorization": f"Bearer {token}"
    }


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["application"] == "SecureTask"


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_register_user():
    response = client.post(
        "/register",
        json={
            "username": "automated_user",
            "email": "automated@example.com",
            "password": "SecurePass123"
        }
    )

    assert response.status_code == 201
    assert response.json()["username"] == "automated_user"
    assert response.json()["email"] == "automated@example.com"

    assert "password" not in response.json()
    assert "password_hash" not in response.json()


def test_duplicate_username():
    client.post(
        "/register",
        json={
            "username": "duplicateuser",
            "email": "first@example.com",
            "password": "SecurePass123"
        }
    )

    response = client.post(
        "/register",
        json={
            "username": "duplicateuser",
            "email": "second@example.com",
            "password": "SecurePass123"
        }
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Username already exists"


def test_duplicate_email():
    client.post(
        "/register",
        json={
            "username": "firstuser",
            "email": "duplicate@example.com",
            "password": "SecurePass123"
        }
    )

    response = client.post(
        "/register",
        json={
            "username": "seconduser",
            "email": "duplicate@example.com",
            "password": "SecurePass123"
        }
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already exists"


def test_invalid_username():
    response = client.post(
        "/register",
        json={
            "username": "bad<script>",
            "email": "invaliduser@example.com",
            "password": "SecurePass123"
        }
    )

    assert response.status_code == 422


def test_short_password():
    response = client.post(
        "/register",
        json={
            "username": "weakpassword",
            "email": "weak@example.com",
            "password": "123"
        }
    )

    assert response.status_code == 422


def test_login_success():
    register_user(
        "loginuser",
        "login@example.com"
    )

    response = client.post(
        "/login",
        json={
            "username": "loginuser",
            "password": "SecurePass123"
        }
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_wrong_password():
    register_user(
        "wrongpassworduser",
        "wrongpassword@example.com"
    )

    response = client.post(
        "/login",
        json={
            "username": "wrongpassworduser",
            "password": "WrongPassword123"
        }
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_login_nonexistent_user():
    response = client.post(
        "/login",
        json={
            "username": "doesnotexist",
            "password": "SecurePass123"
        }
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_me_requires_authentication():
    response = client.get("/me")

    assert response.status_code == 401


def test_me_returns_current_user():
    register_user(
        "meuser",
        "me@example.com"
    )

    token = login_user("meuser")

    response = client.get(
        "/me",
        headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert response.json()["username"] == "meuser"
    assert response.json()["email"] == "me@example.com"


def test_create_task():
    register_user(
        "taskuser",
        "task@example.com"
    )

    token = login_user("taskuser")

    response = client.post(
        "/tasks",
        headers=auth_headers(token),
        json={
            "title": "Complete security project",
            "description": "Finish the DevSecOps pipeline"
        }
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Complete security project"
    assert response.json()["description"] == "Finish the DevSecOps pipeline"
    assert response.json()["completed"] is False
    assert response.json()["owner_id"] == 1


def test_tasks_require_authentication():
    response = client.get("/tasks")

    assert response.status_code == 401


def test_get_tasks_only_returns_current_users_tasks():
    register_user(
        "userone",
        "userone@example.com"
    )

    token_one = login_user("userone")

    client.post(
        "/tasks",
        headers=auth_headers(token_one),
        json={
            "title": "User One Task",
            "description": "Private task"
        }
    )

    register_user(
        "usertwo",
        "usertwo@example.com"
    )

    token_two = login_user("usertwo")

    client.post(
        "/tasks",
        headers=auth_headers(token_two),
        json={
            "title": "User Two Task",
            "description": "Another private task"
        }
    )

    response = client.get(
        "/tasks",
        headers=auth_headers(token_one)
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "User One Task"


def test_get_own_task():
    register_user(
        "getuser",
        "get@example.com"
    )

    token = login_user("getuser")

    create_response = client.post(
        "/tasks",
        headers=auth_headers(token),
        json={
            "title": "Task to retrieve",
            "description": "Retrieve this task"
        }
    )

    task_id = create_response.json()["id"]

    response = client.get(
        f"/tasks/{task_id}",
        headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert response.json()["id"] == task_id
    assert response.json()["title"] == "Task to retrieve"


def test_user_cannot_access_another_users_task():
    register_user(
        "owneruser",
        "owner@example.com"
    )

    owner_token = login_user("owneruser")

    create_response = client.post(
        "/tasks",
        headers=auth_headers(owner_token),
        json={
            "title": "Private task",
            "description": "Only owner should access this"
        }
    )

    task_id = create_response.json()["id"]

    register_user(
        "attackeruser",
        "attacker@example.com"
    )

    attacker_token = login_user("attackeruser")

    response = client.get(
        f"/tasks/{task_id}",
        headers=auth_headers(attacker_token)
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_update_own_task():
    register_user(
        "updateuser",
        "update@example.com"
    )

    token = login_user("updateuser")

    create_response = client.post(
        "/tasks",
        headers=auth_headers(token),
        json={
            "title": "Original title",
            "description": "Original description"
        }
    )

    task_id = create_response.json()["id"]

    response = client.put(
        f"/tasks/{task_id}",
        headers=auth_headers(token),
        json={
            "title": "Updated title",
            "completed": True
        }
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated title"
    assert response.json()["description"] == "Original description"
    assert response.json()["completed"] is True


def test_user_cannot_update_another_users_task():
    register_user(
        "updateowner",
        "updateowner@example.com"
    )

    owner_token = login_user("updateowner")

    create_response = client.post(
        "/tasks",
        headers=auth_headers(owner_token),
        json={
            "title": "Owner task",
            "description": "Do not modify"
        }
    )

    task_id = create_response.json()["id"]

    register_user(
        "updateattacker",
        "updateattacker@example.com"
    )

    attacker_token = login_user("updateattacker")

    response = client.put(
        f"/tasks/{task_id}",
        headers=auth_headers(attacker_token),
        json={
            "title": "Malicious modification"
        }
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_delete_own_task():
    register_user(
        "deleteuser",
        "delete@example.com"
    )

    token = login_user("deleteuser")

    create_response = client.post(
        "/tasks",
        headers=auth_headers(token),
        json={
            "title": "Task to delete",
            "description": "Delete this task"
        }
    )

    task_id = create_response.json()["id"]

    response = client.delete(
        f"/tasks/{task_id}",
        headers=auth_headers(token)
    )

    assert response.status_code == 204

    get_response = client.get(
        f"/tasks/{task_id}",
        headers=auth_headers(token)
    )

    assert get_response.status_code == 404


def test_user_cannot_delete_another_users_task():
    register_user(
        "deleteowner",
        "deleteowner@example.com"
    )

    owner_token = login_user("deleteowner")

    create_response = client.post(
        "/tasks",
        headers=auth_headers(owner_token),
        json={
            "title": "Protected task",
            "description": "Should remain"
        }
    )

    task_id = create_response.json()["id"]

    register_user(
        "deleteattacker",
        "deleteattacker@example.com"
    )

    attacker_token = login_user("deleteattacker")

    response = client.delete(
        f"/tasks/{task_id}",
        headers=auth_headers(attacker_token)
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"