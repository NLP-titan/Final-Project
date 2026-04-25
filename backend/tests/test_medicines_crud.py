def test_list_medicines_is_public(client):
    resp = client.get("/api/medicines?limit=5")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) > 0


def test_filter_by_query_and_covered(client):
    resp = client.get("/api/medicines?q=paracetamol")
    assert resp.status_code == 200
    names = [m["name"].lower() for m in resp.json()]
    assert any("paracetamol" in n for n in names)

    resp = client.get("/api/medicines?covered=false")
    assert resp.status_code == 200
    assert all(m["covered"] is False for m in resp.json())


def test_create_requires_admin(client, user_headers):
    resp = client.post(
        "/api/medicines",
        headers=user_headers,
        json={"name": "X", "generic_name": "x", "covered": True},
    )
    assert resp.status_code == 403


def test_admin_full_crud(client, admin_headers):
    resp = client.post(
        "/api/medicines",
        headers=admin_headers,
        json={
            "name": "Newdrug",
            "generic_name": "newdrug",
            "strength": "10mg",
            "form": "tablet",
            "covered": True,
        },
    )
    assert resp.status_code == 201, resp.text
    new_id = resp.json()["id"]

    resp = client.patch(
        f"/api/medicines/{new_id}",
        headers=admin_headers,
        json={"covered": False, "notes": "Removed from formulary"},
    )
    assert resp.status_code == 200
    assert resp.json()["covered"] is False
    assert "Removed" in resp.json()["notes"]

    # Public can read it
    resp = client.get(f"/api/medicines/{new_id}")
    assert resp.status_code == 200

    # Delete
    resp = client.delete(f"/api/medicines/{new_id}", headers=admin_headers)
    assert resp.status_code == 204
    assert client.get(f"/api/medicines/{new_id}").status_code == 404
