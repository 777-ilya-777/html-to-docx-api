
from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import settings, strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    rule,
)

from src.models import Feedback, Prompt
from src.pony_storage import PonyStorage


class PonyEntityMachine(RuleBasedStateMachine):
    """Проверяет операции с Prompt и Feedback в SQLite."""

    def __init__(self):
        """Создаёт временную базу и эталонные модели."""
        super().__init__()
        self.temp_dir = TemporaryDirectory()
        path = Path(self.temp_dir.name) / "entities.sqlite"
        self.storage = PonyStorage(path)
        self.models = {"prompt": {}, "feedback": {}}

    def make_record(self, entity, uid, value):
        """Создаёт запись указанной сущности."""
        if entity == "prompt":
            return Prompt(uid, 1234567890, value, 1)
        return Feedback(
            uid=uid,
            datetime=1234567890,
            response=value,
            status="success",
            error="",
            prompt=uid,
            cache_hit=0,
            duration=10,
        )

    def changes_for(self, entity, value):
        """Возвращает изменяемое поле сущности."""
        if entity == "prompt":
            return {"parameter": value}
        return {"response": value}

    @rule(
        entity=st.sampled_from(["prompt", "feedback"]),
        uid=st.integers(min_value=1, max_value=20),
        value=st.sampled_from(["first", "second", "third"]),
    )
    def add_record(self, entity, uid, value):
        """Проверяет добавление и отклонение дубликатов."""
        record = self.make_record(entity, uid, value)
        if uid in self.models[entity]:
            try:
                self.storage.add(entity, record)
            except ValueError:
                return
            raise AssertionError("Дубликат был добавлен")
        result = self.storage.add(entity, record)
        self.models[entity][uid] = record
        assert result == record

    @rule(
        entity=st.sampled_from(["prompt", "feedback"]),
        uid=st.integers(min_value=1, max_value=20),
    )
    def query_record(self, entity, uid):
        """Сравнивает поиск записи с эталонной моделью."""
        result = self.storage.query(entity, uid)
        assert result == self.models[entity].get(uid)

    @rule(
        entity=st.sampled_from(["prompt", "feedback"]),
        uid=st.integers(min_value=1, max_value=20),
        value=st.sampled_from(["updated", "changed"]),
    )
    def update_record(self, entity, uid, value):
        """Проверяет изменение и отсутствие записи."""
        changes = self.changes_for(entity, value)
        if uid not in self.models[entity]:
            try:
                self.storage.update(entity, uid, changes)
            except ValueError:
                return
            raise AssertionError("Отсутствующая запись обновлена")
        result = self.storage.update(entity, uid, changes)
        expected = self.models[entity][uid]
        for name, new_value in changes.items():
            setattr(expected, name, new_value)
        assert result == expected

    @rule(
        entity=st.sampled_from(["prompt", "feedback"]),
        uid=st.integers(min_value=1, max_value=20),
    )
    def prune_record(self, entity, uid):
        """Проверяет удаление существующей и отсутствующей записи."""
        expected = uid in self.models[entity]
        result = self.storage.prune(entity, uid)
        assert result is expected
        self.models[entity].pop(uid, None)

    @invariant()
    def check_all_records(self):
        """Сравнивает содержимое SQLite с эталонными моделями."""
        for entity, expected in self.models.items():
            records = self.storage.query(entity)
            actual = {record.uid: record for record in records}
            assert actual == expected

    def teardown(self):
        """Закрывает соединение и удаляет временную базу."""
        self.storage.db.disconnect()
        self.temp_dir.cleanup()


TestPonyEntities = PonyEntityMachine.TestCase
TestPonyEntities.settings = settings(
    max_examples=25,
    stateful_step_count=20,
    deadline=None,
)
