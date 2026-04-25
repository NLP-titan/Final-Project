def test_list_facilities_is_public(client):
    resp = client.get("/api/facilities?limit=5")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_filter_by_region_and_accredited(client):
    resp = client.get("/api/facilities?region=Greater Accra")
    assert resp.status_code == 200
    body = resp.json()
    assert all(f["region"] == "Greater Accra" for f in body)

    resp = client.get("/api/facilities?accredited=false")
    assert resp.status_code == 200
    assert all(f["accredited"] is False for f in resp.json())


def test_create_requires_admin(client, user_headers):
    resp = client.post(
        "/api/facilities",
        headers=user_headers,
        json={"name": "Test Clinic"},
    )
    assert resp.status_code == 403


def test_admin_full_crud(client, admin_headers):
    resp = client.post(
        "/api/facilities",
        headers=admin_headers,
        json={
            "name": "New Clinic",
            "type": "Health Centre",
            "region": "Volta",
            "town": "Aflao",
            "accredited": True,
            "accreditation_status": "Active",
        },
    )
    assert resp.status_code == 201, resp.text
    new_id = resp.json()["id"]

    resp = client.patch(
        f"/api/facilities/{new_id}",
        headers=admin_headers,
        json={"accredited": False, "accreditation_status": "Suspended"},
    )
    assert resp.status_code == 200
    assert resp.json()["accredited"] is False

    resp = client.delete(f"/api/facilities/{new_id}", headers=admin_headers)
    assert resp.status_code == 204
    assert client.get(f"/api/facilities/{new_id}").status_code == 404
