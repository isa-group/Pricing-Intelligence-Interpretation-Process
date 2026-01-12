from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
import pytest
from pydantic import HttpUrl

from harvey_api.app import app, pricing_context_db, container, DbUrlItem


client = TestClient(app)


def test_reject_non_yaml_files():

    files = {"file": ("not_yaml.txt", "This is not yaml", "text/plain")}
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid Content-Type: text/plain. Only application/yaml is supported"
    }


def test_upload_yaml_file():

    filename = "test.yaml"
    files = {"file": (filename, "foo: bar\nbar: baz\n", "application/yaml")}
    response = client.post("/upload", files=files)
    assert response.status_code == 201
    response_body = response.json()
    assert response_body["filename"] == filename
    assert response_body["relative_path"] == "/static/" + filename


def test_delete_yaml_file():

    filename = "test.yaml"
    files = {"file": (filename, "foo: bar\nbar: baz\n", "application/yaml")}
    client.post("/upload", files=files)

    response = client.delete(f"/pricing/{filename}")
    assert response.status_code == 204


def test_delete_non_existent_file():

    filename = "non_existent_file"
    response = client.delete(f"/pricing/{filename}")
    assert response.status_code == 404
    response_body = response.json()
    assert response_body["detail"] == f"File with name {filename} doesn't exist"



def test_url_done_update(monkeypatch):

    filename = "a7874223-be01-469d-95e3-04b17599f95c"
    test_url = "https://example.org/pricing"
    monkeypatch.setitem(
        pricing_context_db, HttpUrl(test_url), {"id": filename, "url": test_url}
    )
    data = {"pricing_url": test_url, "yaml_content": "saasName: Testing"}
    response = client.post("/events/url-transform", json=data)
    assert response.status_code == 201


async def mock_handle_question(*args, **kwargs):
    return {"answer": "Test answer", "plan": {}, "result": {}}

def test_chat_single_url(monkeypatch):
    monkeypatch.setattr(
        container.agent,
        "handle_question",
        mock_handle_question,
    )
    
    test_url = {
        "id": "08a81efd-266c-4580-8b73-484834b76b94",
        "url": "https://example.org/pricing",
    }

    data = {"question": "Will it work?", "pricing_url": test_url}
    response = client.post("/chat", json=data)
    assert response.status_code == 200
    assert pricing_context_db[test_url["url"]] is not None
    db_keys = list(pricing_context_db.keys())
    assert isinstance(db_keys[0], str)
    assert isinstance(pricing_context_db[test_url["url"]], DbUrlItem)
    assert pricing_context_db[test_url["url"]].id == test_url["id"]

def test_chat_multiple_urls(monkeypatch):

    monkeypatch.setattr(
        container.agent,
        "handle_question",
        mock_handle_question,
    )

    test_url_first = {
        "id": "08a81efd-266c-4580-8b73-484834b76b94",
        "url": "https://example.org/pricing",
    }
    test_url_second = {
        "id": "94bab2da-b4cb-478c-a5f9-9aaf3633b8a8",
        "url": "https://test.com/pricing",
    }
    test_urls = [test_url_first, test_url_second]
    data = {"question": "Will it work?", "pricing_urls": test_urls}
    response = client.post("/chat", json=data)
    assert response.status_code == 200
    assert pricing_context_db[test_url_first["url"]] is not None
    for test_url in test_urls:
        assert pricing_context_db[test_url["url"]].id == test_url["id"]
