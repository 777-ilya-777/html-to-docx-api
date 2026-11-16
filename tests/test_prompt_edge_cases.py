
import pytest

from src import api
from src.storage import FileStorage
from tests.test_api import send_request


HEADERS = {
    "Content-Type": "text/json",
    "Accept": "text/json",
    "Accept-Language": "ru-RU",
}

HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_CONFLICT = 409

SESSION_UID = 1
PROMPT_UID = 10
EXPECTED_PROMPT_COUNT = 1


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
    assert result["status"] == HTTP_OK


def add_prompt(uid, test_mode):
    """Создаёт запрос через HTTP API."""
    path = (
        f"/public/api/prompt/add/{uid}"
        f"?session={SESSION_UID}&parameter=example1.html"
        f"&test_mode={test_mode}"
    )
    return send_request("PUT", path, HEADERS)


def test_prompt_invalid_test_mode():
    """Отклоняет недопустимое значение test_mode."""
    add_session(SESSION_UID)

    result = add_prompt(PROMPT_UID, "invalid")

    assert result["status"] == HTTP_BAD_REQUEST
    assert api.storage.query("prompt", PROMPT_UID) is None


def test_prompt_duplicate_uid():
    """Отклоняет повторное создание Prompt."""
    add_session(SESSION_UID)

    first = add_prompt(PROMPT_UID, "1")
    second = add_prompt(PROMPT_UID, "1")

    assert first["status"] == HTTP_OK
    assert second["status"] == HTTP_CONFLICT

    prompts = api.storage.query("prompt")
    assert len(prompts) == EXPECTED_PROMPT_COUNT
    assert prompts[0].uid == PROMPT_UID
