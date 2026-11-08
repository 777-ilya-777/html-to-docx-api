
from tempfile import TemporaryDirectory
from pathlib import Path

from hypothesis import settings, strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    rule,
)

from src.models import Session
from src.pony_storage import PonyStorage


class PonySessionMachine(RuleBasedStateMachine):
    """Проверяет SQLite-хранилище на модели Session."""

    def __init__(self):
        """Создаёт изолированную базу и эталонную модель."""
        super().__init__()
        self.temp_dir = TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test.sqlite"
        self.storage = PonyStorage(database_path)
        self.model = {}

    @rule(
        uid=st.integers(min_value=1, max_value=20),
        locale=st.sampled_from(["ru-RU", "en-US", "de-DE"]),
    )
    def add_session(self, uid, locale):
        """Сравнивает добавление с эталонной моделью."""
        record = Session(uid, 1234567890, locale)
        if uid in self.model:
            try:
                self.storage.add("session", record)
            except ValueError:
                return
            raise AssertionError("Дубликат был добавлен")
        result = self.storage.add("session", record)
        self.model[uid] = record
        assert result == record

    @rule(uid=st.integers(min_value=1, max_value=20))
    def query_session(self, uid):
        """Проверяет получение записи по идентификатору."""
        result = self.storage.query("session", uid)
        assert result == self.model.get(uid)

    @rule(
        uid=st.integers(min_value=1, max_value=20),
        locale=st.sampled_from(["ru-RU", "en-US", "de-DE"]),
    )
    def update_session(self, uid, locale):
        """Проверяет изменение существующей записи."""
        if uid not in self.model:
            try:
                self.storage.update(
                    "session", uid, {"locale": locale}
                )
            except ValueError:
                return
            raise AssertionError("Отсутствующая запись обновлена")
        result = self.storage.update(
            "session", uid, {"locale": locale}
        )
        expected = Session(
            uid,
            self.model[uid].datetime,
            locale,
        )
        self.model[uid] = expected
        assert result == expected

    @rule(uid=st.integers(min_value=1, max_value=20))
    def prune_session(self, uid):
        """Проверяет удаление записи."""
        expected = uid in self.model
        result = self.storage.prune("session", uid)
        assert result is expected
        self.model.pop(uid, None)

    @invariant()
    def check_all_sessions(self):
        """Сравнивает всё содержимое базы с моделью."""
        records = self.storage.query("session")
        actual = {record.uid: record for record in records}
        assert actual == self.model

    def teardown(self):
        """Освобождает временные файлы тестовой базы."""
        self.storage.db.disconnect()
        self.temp_dir.cleanup()


TestPonySession = PonySessionMachine.TestCase
TestPonySession.settings = settings(
    max_examples=25,
    stateful_step_count=20,
    deadline=None,
)
