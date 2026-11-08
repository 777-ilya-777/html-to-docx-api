
import json
from dataclasses import asdict
from pathlib import Path

from src.models import Feedback, Prompt, Session


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

MODELS = {
    "session": Session,
    "prompt": Prompt,
    "feedback": Feedback,
}


class FileStorage:
    """Хранит записи сущностей в JSON-файлах."""

    def __init__(self, data_dir=DATA_DIR):
        """Создаёт каталог для хранения данных."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, entity):
        """Возвращает путь к файлу сущности."""
        if entity not in MODELS:
            raise ValueError("Неизвестная сущность")
        return self.data_dir / f"{entity}.json"

    def _read(self, entity):
        """Читает записи из JSON-файла."""
        path = self._path(entity)
        if not path.exists():
            return {}
        with path.open(encoding="utf-8") as file:
            return json.load(file)

    def _write(self, entity, records):
        """Сохраняет записи в JSON-файл."""
        path = self._path(entity)
        with path.open("w", encoding="utf-8") as file:
            json.dump(records, file, ensure_ascii=False, indent=2)

    def add(self, entity, record):
        """Добавляет запись в хранилище."""
        records = self._read(entity)
        key = str(record.uid)
        if key in records:
            raise ValueError("Запись уже существует")
        records[key] = asdict(record)
        self._write(entity, records)
        return record

    def query(self, entity, uid=None):
        """Возвращает одну запись или все записи."""
        records = self._read(entity)
        model = MODELS[entity]
        if uid is not None:
            data = records.get(str(uid))
            return model(**data) if data is not None else None
        return [model(**data) for data in records.values()]

    def update(self, entity, uid, changes):
        """Обновляет существующую запись."""
        records = self._read(entity)
        key = str(uid)
        if key not in records:
            raise ValueError("Запись не найдена")
        records[key].update(changes)
        self._write(entity, records)
        return MODELS[entity](**records[key])

    def prune(self, entity, uid):
        """Удаляет запись по идентификатору."""
        records = self._read(entity)
        key = str(uid)
        if key not in records:
            return False
        del records[key]
        self._write(entity, records)
        return True
