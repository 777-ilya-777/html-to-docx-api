
import pytest

from src.pony_storage import PonyStorage


def test_unknown_entity(tmp_path):
    """Проверяет отклонение неизвестной сущности."""
    database_path = tmp_path / "errors.sqlite"
    storage = PonyStorage(database_path)

    try:
        with pytest.raises(
            ValueError,
            match="Неизвестная сущность",
        ):
            storage.query("unknown")
    finally:
        storage.db.disconnect()
