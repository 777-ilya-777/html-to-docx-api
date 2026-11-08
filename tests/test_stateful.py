
import json
import tempfile
from urllib.parse import urlencode

from hypothesis import settings, strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    rule,
)

from src import api
from src.storage import FileStorage
from tests.test_api import send_request


HEADERS = {
    "Content-Type": "text/json",
    "Accept": "text/json",
    "Accept-Language": "ru-RU",
}


class SessionStateMachine(RuleBasedStateMachine):
    """Проверяет последовательности операций с Session."""

    def __init__(self):
        """Создаёт изолированное хранилище и модель."""
        super().__init__()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_storage = api.storage
        api.storage = FileStorage(self.temp_dir.name)
        self.sessions = {}

    def teardown(self):
        """Восстанавливает хранилище после теста."""
        api.storage = self.original_storage
        self.temp_dir.cleanup()

    def send(self, method, path, params=None, body=None):
        """Отправляет HTTP-запрос к приложению."""
        if params:
            path = f"{path}?{urlencode(params)}"
        payload = None if body is None else json.dumps(body)
        return send_request(method, path, HEADERS, payload)

    @rule(
        uid=st.integers(min_value=1, max_value=20),
        locale=st.sampled_from(["ru-RU", "en-US"]),
    )
    def add_session(self, uid, locale):
        """Проверяет создание Session."""
        path = f"/public/api/session/add/{uid}"
        result = self.send("PUT", path, {"locale": locale})
        expected = 409 if uid in self.sessions else 200
        assert result["status"] == expected
        if expected == 200:
            self.sessions[uid] = locale

    @rule(uid=st.integers(min_value=1, max_value=20))
    def query_session(self, uid):
        """Проверяет поиск Session."""
        result = self.send(
            "POST",
            "/public/api/session/query",
            {"uid": uid},
        )
        expected = 200 if uid in self.sessions else 404
        assert result["status"] == expected
        if expected == 200:
            data = json.loads(result["body"])
            assert data["locale"] == self.sessions[uid]

    @rule(
        uid=st.integers(min_value=1, max_value=20),
        locale=st.sampled_from(["ru-RU", "en-US"]),
    )
    def update_session(self, uid, locale):
        """Проверяет обновление Session."""
        result = self.send(
            "POST",
            "/public/api/session/update",
            {"uid": uid, "locale": locale},
        )
        expected = 200 if uid in self.sessions else 404
        assert result["status"] == expected
        if expected == 200:
            self.sessions[uid] = locale

    @rule(uid=st.integers(min_value=1, max_value=20))
    def prune_session(self, uid):
        """Проверяет удаление Session."""
        result = self.send(
            "POST",
            "/public/api/session/prune",
            body={"uid": uid},
        )
        assert result["status"] == 200
        data = json.loads(result["body"])
        expected = uid in self.sessions
        assert data["deleted"] == expected
        self.sessions.pop(uid, None)

    @invariant()
    def stored_sessions_match_model(self):
        """Сравнивает записи хранилища с моделью."""
        records = api.storage.query("session")
        actual = {
            record.uid: record.locale
            for record in records
        }
        assert actual == self.sessions


TestSessionStateMachine = SessionStateMachine.TestCase
TestSessionStateMachine.settings = settings(
    max_examples=25,
    stateful_step_count=20,
    deadline=None,
)
