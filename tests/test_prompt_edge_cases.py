

import pytest

from src import api
from src.storage import FileStorage
from tests.test_api import send_request


HEADERS = {
    "Content-Type": "text/json",
    "Accept": "text/json",
    "Accept-Language": "ru-RU",
}


@pytest.fixture(autouse=True)
def isolated_storage(monkeypatch, tmp_path):
    """Создаёт отдельное хранилище для каждого теста."""
    monkeypatch.setattr(api, "storage", FileStorage(tmp_path))


def add_session(uid):
    """Создаёт сеанс через HTTP API."""
    result = send_request(
        "PUT",
        f"/public/api/session/add/{uid}?locale=ru-RU",
        HEADERS,
    )
    assert result["status"] == 200


def add_prompt(uid, test_mode):
    """Создаёт запрос через HTTP API."""
    path = (
        f"/public/api/prompt/add/{uid}"
        f"?session=1&parameter=example1.html"
        f"&test_mode={test_mode}"
    )
    return send_request("PUT", path, HEADERS)


def test_prompt_invalid_test_mode():
    """Отклоняет недопустимое значение test_mode."""
    add_session(1)

    result = add_prompt(10, "invalid")

    assert result["status"] == 400
    assert api.storage.query("prompt", 10) is None


def test_prompt_duplicate_uid():
    """Отклоняет повторное создание Prompt."""
    add_session(1)

    first = add_prompt(10, "1")
    second = add_prompt(10, "1")

    assert first["status"] == 200
    assert second["status"] == 409

    prompts = api.storage.query("prompt")
    assert len(prompts) == 1
    assert prompts[0].uid == 10
