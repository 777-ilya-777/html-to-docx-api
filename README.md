# HTML to DOCX API

**Тема курсовой работы:** «Веб-приложение с HTTP API для асинхронного преобразования файлов из формата HTML в формат Docx».

**Практическая работа № 2, вариант № 1.**

## Описание проекта

Приложение на Python для преобразования HTML-файлов в документы DOCX.

Проект включает три этапа:

1. CLI-утилита преобразования HTML в DOCX.
2. HTTP API на Bottle и модельное тестирование с Hypothesis.
3. Хранение данных в SQLite с использованием PonyORM.

Все три этапа реализованы.

## Возможности

- Преобразование HTML-файлов в DOCX.
- Поддержка заголовков, абзацев, списков и базового форматирования текста.
- Запуск преобразования из командной строки.
- HTTP API для управления сеансами и запросами.
- Сохранение результатов обработки.
- Формирование отчёта по связанным данным.
- Хранение записей в SQLite через PonyORM.
- Модельное тестирование с Hypothesis.
- Измерение покрытия кода и ветвей выполнения.

## Структура проекта

```text
html-to-docx-api/
├── src/
│   ├── api.py
│   ├── cli.py
│   ├── models.py
│   ├── storage.py
│   └── pony_storage.py
├── tests/
├── data/
├── example1.html
├── example2.html
├── example3.html
├── example4.html
├── example5.html
├── requirements.txt
├── run.bat
├── .gitignore
└── README.md
```

`storage.py` содержит файловое хранилище второго этапа.

`pony_storage.py` реализует хранилище SQLite третьего этапа.

`api.py` по умолчанию использует PonyORM.

Каталог `data` создаётся автоматически. Файлы SQLite и результаты преобразования не включаются в Git.

## Требования

- Python 3.11.
- Зависимости из `requirements.txt`.

Основные библиотеки: Bottle, PonyORM, python-docx, lxml.

Для автоматического тестирования используются pytest, Hypothesis и Coverage.

## Установка

Создание виртуального окружения:

```powershell
py -3.11 -m venv .venv
```

Активация:

```powershell
.\.venv\Scripts\Activate.ps1
```

Установка зависимостей приложения:

```powershell
python -m pip install -r requirements.txt
```

Установка инструментов тестирования:

```powershell
python -m pip install pytest hypothesis coverage ruff
```

## Запуск CLI

```powershell
python -m src.cli example1.html example1.docx
```

Первый аргумент — путь к исходному HTML-файлу, второй — путь к создаваемому DOCX-файлу.

Также доступен запуск через `run.bat`:

```powershell
.\run.bat example1.html example1.docx
```

## Запуск HTTP API

```powershell
python -m src.api
```

Сервер запускается по адресу `http://127.0.0.1:8080`.

Для запросов необходимы заголовки:

- `Content-Type: text/json` — для POST и PUT.
- `Accept: text/json`.
- `Accept-Language: ru-RU`.

## Маршруты HTTP API

| Метод | Маршрут | Назначение |
|---|---|---|
| PUT | `/public/api/session/add/:uid` | Создание сеанса |
| POST | `/public/api/session/prune` | Удаление сеанса |
| POST | `/public/api/session/query` | Поиск сеанса |
| POST | `/public/api/session/update` | Изменение сеанса |
| PUT | `/public/api/prompt/add/:uid` | Создание запроса |
| POST | `/public/api/prompt/prune` | Удаление запроса |
| POST | `/public/api/prompt/query/:session` | Запросы сеанса |
| POST | `/public/api/prompt/update` | Изменение запроса |
| POST | `/public/api/feedback/query/:prompt` | Результаты обработки |
| POST | `/public/api/report/query` | Формирование отчёта |

Параметры передаются через URL, строку запроса или JSON-тело в зависимости от маршрута.

Для `prompt/add` предусмотрен параметр `test_mode=1`, позволяющий пропустить фактическое преобразование при тестировании.

В обычном режиме API вызывает CLI-преобразователь через `subprocess`.

## Хранение данных

Приложение использует SQLite и PonyORM.

База данных автоматически создаётся в файле:

```text
data/app.sqlite
```

В базе представлены три сущности:

- `Session` — пользовательский сеанс.
- `Prompt` — запрос на преобразование.
- `Feedback` — результат обработки.

Хранилище реализует операции `add`, `query`, `update` и `prune`.

## Тестирование

Запуск всех тестов:

```powershell
python -m pytest tests -q
```

На момент завершения третьего этапа успешно проходят **38 тестов**.

Для модельного тестирования используется `hypothesis.stateful.RuleBasedStateMachine`.

Проверяются HTTP API, файловое хранилище второго этапа и SQLite-хранилище третьего этапа.

## Покрытие кода

Запуск тестов с измерением покрытия ветвей:

```powershell
python -m coverage run --branch --source=src.api,src.pony_storage -m pytest tests -q
```

Просмотр отчёта:

```powershell
python -m coverage report -m
```

Результаты проверки третьего этапа:

- `src/api.py` — 96%.
- `src/pony_storage.py` — 100%.
- Общее покрытие — 98%.

Все ветви HTTP-обработчиков проверены. Непокрытая ветвь в `api.py` относится к непосредственному запуску сервера.

## Проверка качества кода

```powershell
python -m ruff check src tests --select E,F,C90 --config "lint.mccabe.max-complexity=5" --config "line-length=80"
```

Код проверяется на соответствие PEP 8 и ограничениям цикломатической сложности.

## Текущий статус

Реализованы CLI-преобразователь, HTTP API и SQLite-хранилище на PonyORM.

Все 38 автоматических тестов проходят. Третий этап находится на стадии окончательной проверки оформления репозитория и подготовки коммита.
