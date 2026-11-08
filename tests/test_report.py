
import json

import pytest

from src import api
from src.models import Feedback, Prompt, Session
from src.storage import FileStorage
from tests.test_api import send_request


HEADERS = {
    "Content-Type": "text/json",
    "Accept": "text/json",
    "Accept-Language": "ru-RU",
}

CURRENT_TIME = 2_000_000_000


@pytest.fixture
def report_storage(monkeypatch, tmp_path):
    """Создаёт изолированное хранилище для отчёта."""
    storage = FileStorage(tmp_path)
    monkeypatch.setattr(api, "storage", storage)
    monkeypatch.setattr(api, "time", lambda: CURRENT_TIME)
    return storage


def add_feedback(storage, uid, prompt, error=""):
    """Добавляет результат обработки запроса."""
    feedback = Feedback(
        uid=uid,
        datetime=CURRENT_TIME,
        response="",
        status="success",
        error=error,
        prompt=prompt,
        cache_hit=0,
        duration=0,
    )
    storage.add("feedback", feedback)


def query_report():
    """Получает отчёт через HTTP API."""
    result = send_request(
        "POST",
        "/public/api/report/query",
        HEADERS,
    )
    assert result["status"] == 200
    return json.loads(result["body"])


def test_report_with_related_records(report_storage):
    """Проверяет соединение трёх сущностей."""
    report_storage.add(
        "session",
        Session(1, CURRENT_TIME, "ru-RU"),
    )
    report_storage.add(
        "prompt",
        Prompt(10, CURRENT_TIME, "example1.html", 1),
    )
    add_feedback(report_storage, 100, 10, "test error")

    assert query_report() == [
        {
            "error": "test error",
            "parameter": "example1.html",
            "locale": "ru-RU",
        }
    ]


def test_report_excludes_old_prompts(report_storage):
    """Исключает запросы старше девяти минут."""
    report_storage.add(
        "session",
        Session(1, CURRENT_TIME, "ru-RU"),
    )
    report_storage.add(
        "prompt",
        Prompt(
            10,
            CURRENT_TIME - api.REPORT_WINDOW_SECONDS - 1,
            "old.html",
            1,
        ),
    )
    add_feedback(report_storage, 100, 10)

    assert query_report() == []


def test_report_excludes_missing_relations(report_storage):
    """Исключает записи без необходимых связей."""
    report_storage.add(
        "prompt",
        Prompt(10, CURRENT_TIME, "orphan.html", 999),
    )
    add_feedback(report_storage, 100, 10)

    report_storage.add(
        "session",
        Session(1, CURRENT_TIME, "en-US"),
    )
    report_storage.add(
        "prompt",
        Prompt(20, CURRENT_TIME, "no_feedback.html", 1),
    )

    assert query_report() == []


def test_report_ignores_unrelated_feedback(report_storage):
    """Не включает результаты других запросов."""
    report_storage.add(
        "session",
        Session(1, CURRENT_TIME, "ru-RU"),
    )
    report_storage.add(
        "prompt",
        Prompt(10, CURRENT_TIME, "example1.html", 1),
    )
    add_feedback(report_storage, 100, 999)
    add_feedback(report_storage, 101, 10)

    assert query_report() == [
        {
            "error": "",
            "parameter": "example1.html",
            "locale": "ru-RU",
        }
    ]
