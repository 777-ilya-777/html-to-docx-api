
from dataclasses import dataclass


@dataclass
class Session:
    """Сеанс пользователя."""

    uid: int
    datetime: int
    locale: str


@dataclass
class Prompt:
    """Запрос на выполнение преобразования."""

    uid: int
    datetime: int
    parameter: str
    session: int


@dataclass
class Feedback:
    """Результат обработки запроса."""

    uid: int
    datetime: int
    response: str
    status: str
    error: str
    prompt: int
    cache_hit: int
    duration: int
