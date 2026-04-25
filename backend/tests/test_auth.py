def test_register_login_me_flow(client):
    # Register
    resp = client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "supersecret1", "full_name": "Alice"},
    )
    assert resp.status_code == 201
    body = resp.json()
    token = body["access_token"]
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["role"] == "user"

    # Me
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"

    # Login again with the same credentials
    resp = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "supersecret1"},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_register_duplicate_email_conflicts(client):
    payload = {"email": "dup@example.com", "password": "supersecret1"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409


def test_login_with_wrong_password_fails(client):
    client.post(
        "/api/auth/register",
        json={"email": "bob@example.com", "password": "rightpassword1"},
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "bob@example.com", "password": "wrongpassword1"},
    )
    assert resp.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


def test_update_me_changes_password(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    resp = client.patch(
        "/api/auth/me", json={"password": "newpassword456", "full_name": "Updated"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Updated"
    # New password works
    assert client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "newpassword456"},
    ).status_code == 200
    # Old password no longer works
    assert client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "supersecret123"},
    ).status_code == 401


def test_admin_can_list_users_user_cannot(client, admin_headers, user_headers):
    assert client.get("/api/users", headers=admin_headers).status_code == 200
    assert client.get("/api/users", headers=user_headers).status_code == 403


def test_admin_cannot_self_deactivate(client, admin_headers):
    me = client.get("/api/auth/me", headers=admin_headers).json()
    resp = client.patch(
        f"/api/users/{me['id']}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert resp.status_code == 400
