
from dataclasses import asdict
from pathlib import Path

from pony.orm import (
    Database,
    Optional,
    PrimaryKey,
    Required,
    db_session,
)

from src.storage import DATA_DIR, MODELS


class PonyStorage:
    """Хранит записи сущностей в базе данных SQLite."""

    def __init__(self, database_path=None):
        """Создаёт базу данных и таблицы сущностей."""
        self.data_dir = DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if database_path is None:
            database_path = self.data_dir / "app.sqlite"

        self.database_path = Path(database_path).resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = Database()
        self.entities = self._create_entities()
        self.db.bind(
            provider="sqlite",
            filename=str(self.database_path),
            create_db=True,
        )
        self.db.generate_mapping(create_tables=True)

    def _create_entities(self):
        """Определяет три ORM-модели базы данных."""

        class SessionEntity(self.db.Entity):
            """Таблица пользовательских сеансов."""

            uid = PrimaryKey(int)
            datetime = Required(int)
            locale = Required(str)

        class PromptEntity(self.db.Entity):
            """Таблица запросов на преобразование."""

            uid = PrimaryKey(int)
            datetime = Required(int)
            parameter = Required(str)
            session = Required(int)

        class FeedbackEntity(self.db.Entity):
            """Таблица результатов обработки запросов."""

            uid = PrimaryKey(int)
            datetime = Required(int)
            response = Optional(str, default="")
            status = Required(str)
            error = Optional(str, default="")
            prompt = Required(int)
            cache_hit = Required(int)
            duration = Required(int)

        return {
            "session": SessionEntity,
            "prompt": PromptEntity,
            "feedback": FeedbackEntity,
        }

    def _entity(self, entity):
        """Возвращает ORM-класс указанной сущности."""
        if entity not in self.entities:
            raise ValueError("Неизвестная сущность")
        return self.entities[entity]

    @db_session
    def add(self, entity, record):
        """Добавляет новую запись в базу данных."""
        model = self._entity(entity)
        if model.get(uid=record.uid) is not None:
            raise ValueError("Запись уже существует")
        model(**asdict(record))
        return record

    @db_session
    def query(self, entity, uid=None):
        """Возвращает одну запись или список записей."""
        model = self._entity(entity)
        dataclass_model = MODELS[entity]
        if uid is not None:
            record = model.get(uid=uid)
            if record is None:
                return None
            return self._to_dataclass(record, dataclass_model)
        return [
            self._to_dataclass(record, dataclass_model)
            for record in model.select()
        ]

    @staticmethod
    def _to_dataclass(record, dataclass_model):
        """Преобразует ORM-запись в объект модели."""
        fields = dataclass_model.__dataclass_fields__
        values = {
            name: getattr(record, name)
            for name in fields
        }
        return dataclass_model(**values)

    @db_session
    def update(self, entity, uid, changes):
        """Обновляет существующую запись."""
        model = self._entity(entity)
        record = model.get(uid=uid)
        if record is None:
            raise ValueError("Запись не найдена")
        for name, value in changes.items():
            setattr(record, name, value)
        return self._to_dataclass(record, MODELS[entity])

    @db_session
    def prune(self, entity, uid):
        """Удаляет запись по идентификатору."""
        model = self._entity(entity)
        record = model.get(uid=uid)
        if record is None:
            return False
        record.delete()
        return True
