
import json

import pytest

from src import api
from src.models import Feedback
from src.storage import FileStorage
from tests.test_api import send_request


HEADERS = {
    "Content-Type": "text/json",
    "Accept": "text/json",
    "Accept-Language": "ru-RU",
}


@pytest.fixture(autouse=True)
def isolated_storage(monkeypatch, tmp_path):
    """Изолирует данные каждого теста."""
    monkeypatch.setattr(api, "storage", FileStorage(tmp_path))


@pytest.mark.parametrize(
    ("method", "path", "body", "expected"),
    [
        ("PUT", "/public/api/session/add/1", None, 400),
        ("POST", "/public/api/session/query", None, 400),
        ("POST", "/public/api/session/query?uid=abc", None, 400),
        ("POST", "/public/api/session/update?uid=1", None, 400),
        ("PUT", "/public/api/prompt/add/1", None, 400),
        ("PUT", "/public/api/prompt/add/1?session=abc", None, 400),
        ("POST", "/public/api/prompt/update?uid=1", None, 400),
        ("POST", "/public/api/session/prune", "{bad}", 400),
        ("POST", "/public/api/session/prune", "[]", 400),
        ("POST", "/public/api/session/prune", "{}", 400),
        ("POST", "/public/api/prompt/prune", "{bad}", 400),
        ("POST", "/public/api/prompt/prune", "{}", 400),
        ("POST", "/public/api/session/query?uid=999", None, 404),
        (
            "POST",
            "/public/api/session/update?uid=999&locale=ru-RU",
            None,
            404,
        ),
        (
            "POST",
            "/public/api/prompt/update?uid=999&parameter=a.html",
            None,
            404,
        ),
        (
            "PUT",
            "/public/api/prompt/add/1?session=999&parameter=a.html",
            None,
            404,
        ),
    ],
)
def test_invalid_requests(method, path, body, expected):
    """Проверяет ошибки параметров и JSON."""
    result = send_request(method, path, HEADERS, body)
    assert result["status"] == expected


@pytest.mark.parametrize(
    ("method", "headers", "expected"),
    [
        (
            "GET",
            {"Accept": "text/json", "Accept-Language": "ru-RU"},
            405,
        ),
        (
            "GET",
            {"Accept": "application/json", "Accept-Language": "ru-RU"},
            406,
        ),
        (
            "POST",
            {"Accept": "text/json", "Accept-Language": "ru-RU"},
            415,
        ),
        (
            "POST",
            {
                "Content-Type": "text/json",
                "Accept": "text/json",
                "Accept-Language": "en-US",
            },
            406,
        ),
    ],
)
def test_header_validation(method, headers, expected):
    """Проверяет приоритет обработки HTTP-заголовков."""
    result = send_request(
        method,
        "/public/api/report/query",
        headers,
    )
    assert result["status"] == expected


def test_feedback_query():
    """Проверяет получение результата обработки Prompt."""
    feedback = Feedback(
        uid=100,
        datetime=1000,
        response="skipped",
        status="test",
        error="",
        prompt=10,
        cache_hit=0,
        duration=0,
    )
    api.storage.add("feedback", feedback)

    result = send_request(
        "POST",
        "/public/api/feedback/query/10",
        HEADERS,
    )

    assert result["status"] == 200
    data = json.loads(result["body"])
    assert len(data) == 1
    assert data[0]["uid"] == 100
    assert data[0]["prompt"] == 10


def test_feedback_query_empty():
    """Проверяет поиск отсутствующих результатов."""
    result = send_request(
        "POST",
        "/public/api/feedback/query/999",
        HEADERS,
    )
    assert result["status"] == 200
    assert json.loads(result["body"]) == []
