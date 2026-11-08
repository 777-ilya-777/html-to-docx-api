from io import BytesIO
from urllib.parse import urlsplit
from wsgiref.util import setup_testing_defaults

import pytest

from src.api import app


def add_request_headers(environ, headers):
    """Добавляет HTTP-заголовки в окружение WSGI."""
    for name, value in (headers or {}).items():
        key = "HTTP_" + name.upper().replace("-", "_")
        if name.lower() == "content-type":
            key = "CONTENT_TYPE"
        environ[key] = value


def close_response(response_body):
    """Закрывает ответ WSGI, если он поддерживает закрытие."""
    if hasattr(response_body, "close"):
        response_body.close()


def send_request(method, path, headers=None, body=None):
    """Отправляет HTTP-запрос непосредственно в Bottle."""
    url = urlsplit(path)
    payload = b"" if body is None else body.encode("utf-8")

    environ = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = method
    environ["PATH_INFO"] = url.path
    environ["QUERY_STRING"] = url.query
    environ["wsgi.input"] = BytesIO(payload)
    environ["CONTENT_LENGTH"] = str(len(payload))
    add_request_headers(environ, headers)

    result = {}

    def start_response(status, response_headers, exc_info=None):
        """Сохраняет статус и заголовки ответа."""
        result["status"] = int(status.split()[0])
        result["headers"] = dict(response_headers)

    response_body = app(environ, start_response)
    result["body"] = b"".join(response_body)
    close_response(response_body)

    return result


@pytest.mark.parametrize(
    ("headers", "expected_status"),
    [
        (
            {
                "Content-Type": "application/json",
                "Accept": "text/json",
                "Accept-Language": "ru-RU",
            },
            415,
        ),
        (
            {
                "Content-Type": "text/json",
                "Accept": "application/json",
                "Accept-Language": "ru-RU",
            },
            406,
        ),
        (
            {
                "Content-Type": "text/json",
                "Accept": "text/json",
                "Accept-Language": "en-US",
            },
            406,
        ),
    ],
)
def test_required_headers(headers, expected_status):
    """Проверяет отклонение неверных HTTP-заголовков."""
    result = send_request(
        "POST",
        "/public/api/report/query",
        headers,
    )
    assert result["status"] == expected_status