from fastapi.testclient import TestClient
import pytest
from pydantic import HttpUrl

from harvey_api.app import app, pricing_context_db

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


def test_upload_file_given_url(monkeypatch):

    filename = "a7874223-be01-469d-95e3-04b17599f95c"
    test_url = "https://example.org/pricing"
    monkeypatch.setitem(
        pricing_context_db, HttpUrl(test_url), {"id": filename, "url": test_url}
    )
    data = {"pricing_url": test_url, "content": "saasName: test\n"}
    response = client.post("/upload/url", json=data)
    assert response.status_code == 201
    response_body = response.json()
    assert response_body["filename"] == filename
