"""Conversation + message persistence and feedback flow."""
import pytest


def _new_conv(client, headers, title=None) -> int:
    resp = client.post("/api/conversations", headers=headers, json={"title": title})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_create_and_post_message_persists_history(client, user_headers):
    conv_id = _new_conv(client, user_headers, title="My chat")

    resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=user_headers,
        json={"content": "Should I pay for Paracetamol?"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user_message"]["role"] == "user"
    assert body["assistant_message"]["role"] == "assistant"
    assert body["assistant_message"]["provider"] == "heuristic"
    assert any(
        tc["name"] == "medicines_checker"
        for tc in body["assistant_message"]["tool_calls"]
    )

    # History reads back
    resp = client.get(f"/api/conversations/{conv_id}", headers=user_headers)
    assert resp.status_code == 200
    detail = resp.json()
    roles = [m["role"] for m in detail["messages"]]
    assert roles == ["user", "assistant"]
    assert detail["title"] == "My chat"


def test_conversation_listing_orders_by_recent(client, user_headers):
    a = _new_conv(client, user_headers, title="A")
    b = _new_conv(client, user_headers, title="B")
    client.post(
        f"/api/conversations/{a}/messages",
        headers=user_headers,
        json={"content": "Hello"},
    )
    resp = client.get("/api/conversations", headers=user_headers)
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert ids[0] == a, "the conversation that received a new message should bubble to top"


def test_user_cannot_access_others_conversations(client, user_headers, admin_headers):
    conv_id = _new_conv(client, user_headers, title="mine")
    resp = client.get(f"/api/conversations/{conv_id}", headers=admin_headers)
    assert resp.status_code == 404  # admin's user_id ≠ owner; isolation enforced


def test_rename_and_delete_conversation(client, user_headers):
    conv_id = _new_conv(client, user_headers)
    resp = client.patch(
        f"/api/conversations/{conv_id}", headers=user_headers, json={"title": "Renamed"}
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Renamed"

    resp = client.delete(f"/api/conversations/{conv_id}", headers=user_headers)
    assert resp.status_code == 204
    assert client.get(f"/api/conversations/{conv_id}", headers=user_headers).status_code == 404


def test_feedback_on_assistant_message(client, user_headers):
    conv_id = _new_conv(client, user_headers)
    resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=user_headers,
        json={"content": "Is Korle Bu accredited?"},
    )
    assistant_id = resp.json()["assistant_message"]["id"]

    resp = client.post(
        f"/api/messages/{assistant_id}/feedback",
        headers=user_headers,
        json={"rating": 1, "comment": "Helpful"},
    )
    assert resp.status_code == 201
    assert resp.json()["rating"] == 1

    # Upsert: posting again updates instead of duplicating
    resp = client.post(
        f"/api/messages/{assistant_id}/feedback",
        headers=user_headers,
        json={"rating": -1, "comment": "Changed my mind"},
    )
    assert resp.status_code == 201
    assert resp.json()["rating"] == -1


def test_chat_endpoint_works_without_auth(client):
    resp = client.post(
        "/api/chat",
        json={"message": "Is dialysis covered?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"]
    assert body["provider"] == "heuristic"
    assert body["tool_calls"]
