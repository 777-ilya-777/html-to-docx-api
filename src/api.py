
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from time import monotonic, time

from bottle import Bottle, HTTPResponse, request

from src.models import Feedback, Prompt, Session
from src.pony_storage import PonyStorage

app = Bottle()
storage = PonyStorage()
REPORT_WINDOW_SECONDS = 9 * 60
MILLISECONDS_PER_SECOND = 1000


@app.hook("before_request")
def validate_headers():
    """Проверяет обязательные HTTP-заголовки."""
    if request.method in {"POST", "PUT", "PATCH"}:
        if request.get_header("Content-Type") != "text/json":
            raise HTTPResponse(status=415)
    if request.get_header("Accept") != "text/json":
        raise HTTPResponse(status=406)
    if request.get_header("Accept-Language") != "ru-RU":
        raise HTTPResponse(status=406)


def json_response(data):
    """Формирует JSON-ответ с типом text/json."""
    return HTTPResponse(
        body=json.dumps(data, ensure_ascii=False),
        status=200,
        headers={"Content-Type": "text/json"},
    )


def get_uid():
    """Получает идентификатор из строки запроса."""
    return get_query_int("uid")


def get_query_int(name):
    """Получает целочисленный параметр запроса."""
    try:
        return int(request.query[name])
    except (KeyError, TypeError, ValueError):
        raise HTTPResponse(status=400) from None


def read_json_body():
    """Читает JSON-тело с обязательным типом text/json."""
    try:
        data = json.loads(request.body.read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPResponse(status=400) from None
    if not isinstance(data, dict):
        raise HTTPResponse(status=400)
    return data


def run_conversion(uid, parameter):
    """Запускает CLI-преобразователь через subprocess."""
    source = Path(parameter)
    output = storage.data_dir / f"prompt_{uid}.docx"
    command = [
        sys.executable, "-m", "src.cli",
        str(source), str(output),
    ]
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )


def create_feedback(uid, response, status, error, duration):
    """Сохраняет результат выполнения Prompt."""
    feedback = Feedback(
        uid=uid,
        datetime=int(time()),
        response=response,
        status=status,
        error=error,
        prompt=uid,
        cache_hit=0,
        duration=duration,
    )
    storage.add("feedback", feedback)
    return feedback


def process_prompt(uid, parameter, test_mode):
    """Выполняет преобразование или пропускает его."""
    if test_mode == "1":
        return "skipped", "test", "", 0
    started = monotonic()
    result = run_conversion(uid, parameter)
    duration = int(
        (monotonic() - started) * MILLISECONDS_PER_SECOND
    )
    if result.returncode != 0:
        return "", "error", result.stderr, duration
    output = storage.data_dir / f"prompt_{uid}.docx"
    return str(output), "success", "", duration


def get_recent_prompts():
    """Возвращает запросы за последние девять минут."""
    cutoff = int(time()) - REPORT_WINDOW_SECONDS
    return [
        prompt for prompt in storage.query("prompt")
        if prompt.datetime >= cutoff
    ]


def build_report_rows(prompt, session, feedbacks):
    """Формирует строки отчёта для одного запроса."""
    return [
        {
            "error": feedback.error,
            "parameter": prompt.parameter,
            "locale": session.locale,
        }
        for feedback in feedbacks
        if feedback.prompt == prompt.uid
    ]


def build_report():
    """Соединяет Session, Prompt и Feedback."""
    sessions = {
        session.uid: session
        for session in storage.query("session")
    }
    feedbacks = storage.query("feedback")
    rows = []
    for prompt in get_recent_prompts():
        session = sessions.get(prompt.session)
        if session is not None:
            rows.extend(
                build_report_rows(prompt, session, feedbacks)
            )
    return rows


@app.put("/public/api/session/add/<uid:int>")
def session_add(uid):
    """Создаёт запись Session."""
    locale = request.query.get("locale")
    if not locale:
        raise HTTPResponse(status=400)
    session = Session(uid, int(time()), locale)
    try:
        storage.add("session", session)
    except ValueError:
        raise HTTPResponse(status=409) from None
    return json_response(asdict(session))


@app.post("/public/api/session/prune")
def session_prune():
    """Удаляет запись Session."""
    data = read_json_body()
    try:
        uid = int(data["uid"])
    except (TypeError, ValueError, KeyError):
        raise HTTPResponse(status=400) from None
    deleted = storage.prune("session", uid)
    return json_response({"deleted": deleted})


@app.post("/public/api/session/query")
def session_query():
    """Ищет запись Session."""
    uid = get_uid()
    session = storage.query("session", uid)
    if session is None:
        raise HTTPResponse(status=404)
    return json_response(asdict(session))


@app.post("/public/api/session/update")
def session_update():
    """Изменяет запись Session."""
    uid = get_uid()
    locale = request.query.get("locale")
    if not locale:
        raise HTTPResponse(status=400)
    try:
        session = storage.update(
            "session", uid, {"locale": locale}
        )
    except ValueError:
        raise HTTPResponse(status=404) from None
    return json_response(asdict(session))


@app.put("/public/api/prompt/add/<uid:int>")
def prompt_add(uid):
    """Создаёт Prompt и сохраняет результат обработки."""
    session_uid = get_query_int("session")
    parameter = request.query.get("parameter")
    test_mode = request.query.get("test_mode", "0")
    if not parameter or test_mode not in {"0", "1"}:
        raise HTTPResponse(status=400)
    if storage.query("session", session_uid) is None:
        raise HTTPResponse(status=404)
    if storage.query("prompt", uid) is not None:
        raise HTTPResponse(status=409)
    response, status, error, duration = process_prompt(
        uid, parameter, test_mode
    )
    prompt = Prompt(
        uid, int(time()), parameter, session_uid
    )
    storage.add("prompt", prompt)
    create_feedback(
        uid, response, status, error, duration
    )
    return json_response(asdict(prompt))


@app.post("/public/api/prompt/prune")
def prompt_prune():
    """Удаляет запись Prompt."""
    data = read_json_body()
    try:
        uid = int(data["uid"])
    except (KeyError, TypeError, ValueError):
        raise HTTPResponse(status=400) from None
    deleted = storage.prune("prompt", uid)
    return json_response({"deleted": deleted})


@app.post("/public/api/prompt/query/<session:int>")
def prompt_query(session):
    """Возвращает запросы указанного сеанса."""
    prompts = storage.query("prompt")
    matches = [
        asdict(prompt)
        for prompt in prompts
        if prompt.session == session
    ]
    return json_response(matches)


@app.post("/public/api/prompt/update")
def prompt_update():
    """Изменяет параметр существующего Prompt."""
    uid = get_uid()
    parameter = request.query.get("parameter")
    if not parameter:
        raise HTTPResponse(status=400)
    try:
        prompt = storage.update(
            "prompt", uid, {"parameter": parameter}
        )
    except ValueError:
        raise HTTPResponse(status=404) from None
    return json_response(asdict(prompt))


@app.post("/public/api/feedback/query/<prompt:int>")
def feedback_query(prompt):
    """Возвращает результаты обработки указанного Prompt."""
    feedbacks = storage.query("feedback")
    matches = [
        asdict(feedback)
        for feedback in feedbacks
        if feedback.prompt == prompt
    ]
    return json_response(matches)


@app.post("/public/api/report/query")
def report_query():
    """Формирует отчёт по трём связанным сущностям."""
    return json_response(build_report())


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=8080,
        debug=True,
    )
