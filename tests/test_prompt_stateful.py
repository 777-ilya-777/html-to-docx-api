
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

UIDS = st.integers(min_value=1, max_value=10)
PARAMETERS = st.sampled_from([
    "example1.html",
    "example2.html",
    "sample.html",
])


class PromptStateMachine(RuleBasedStateMachine):
    """Проверяет последовательности операций с Prompt."""

    def __init__(self):
        """Создаёт изолированное хранилище и модель."""
        super().__init__()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_storage = api.storage
        api.storage = FileStorage(self.temp_dir.name)
        self.sessions = set()
        self.prompts = {}

    def teardown(self):
        """Восстанавливает исходное хранилище."""
        api.storage = self.original_storage
        self.temp_dir.cleanup()

    def send(self, method, path, params=None, body=None):
        """Отправляет запрос непосредственно в Bottle."""
        if params:
            path = f"{path}?{urlencode(params)}"
        payload = None if body is None else json.dumps(body)
        return send_request(method, path, HEADERS, payload)

    @rule(uid=UIDS)
    def add_session(self, uid):
        """Создаёт сеанс для привязки запросов."""
        path = f"/public/api/session/add/{uid}"
        result = self.send("PUT", path, {"locale": "ru-RU"})
        expected = 409 if uid in self.sessions else 200
        assert result["status"] == expected
        if expected == 200:
            self.sessions.add(uid)

    @rule(uid=UIDS, session=UIDS, parameter=PARAMETERS)
    def add_prompt(self, uid, session, parameter):
        """Проверяет создание Prompt."""
        path = f"/public/api/prompt/add/{uid}"
        params = {
            "session": session,
            "parameter": parameter,
            "test_mode": 1,
        }
        result = self.send("PUT", path, params)

        if session not in self.sessions:
            expected = 404
        elif uid in self.prompts:
            expected = 409
        else:
            expected = 200

        assert result["status"] == expected
        if expected == 200:
            self.prompts[uid] = (session, parameter)

    @rule(session=UIDS)
    def query_prompts(self, session):
        """Проверяет поиск запросов по сеансу."""
        path = f"/public/api/prompt/query/{session}"
        result = self.send("POST", path)
        assert result["status"] == 200

        actual = json.loads(result["body"])
        actual_data = {
            item["uid"]: item["parameter"]
            for item in actual
        }
        expected_data = {
            uid: parameter
            for uid, (session_uid, parameter) in self.prompts.items()
            if session_uid == session
        }
        assert actual_data == expected_data

    @rule(uid=UIDS, parameter=PARAMETERS)
    def update_prompt(self, uid, parameter):
        """Проверяет изменение параметра Prompt."""
        result = self.send(
            "POST",
            "/public/api/prompt/update",
            {"uid": uid, "parameter": parameter},
        )
        expected = 200 if uid in self.prompts else 404
        assert result["status"] == expected

        if expected == 200:
            session, _ = self.prompts[uid]
            self.prompts[uid] = (session, parameter)

    @rule(uid=UIDS)
    def prune_prompt(self, uid):
        """Проверяет удаление Prompt."""
        result = self.send(
            "POST",
            "/public/api/prompt/prune",
            body={"uid": uid},
        )
        assert result["status"] == 200

        actual = json.loads(result["body"])
        expected = uid in self.prompts
        assert actual["deleted"] == expected
        self.prompts.pop(uid, None)

    @invariant()
    def stored_prompts_match_model(self):
        """Сравнивает хранилище с ожидаемыми данными."""
        records = api.storage.query("prompt")
        actual = {
            item.uid: (item.session, item.parameter)
            for item in records
        }
        assert actual == self.prompts


TestPromptStateMachine = PromptStateMachine.TestCase
TestPromptStateMachine.settings = settings(
    max_examples=25,
    stateful_step_count=20,
    deadline=None,
)
