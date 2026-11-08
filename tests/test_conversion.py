
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import api


@pytest.mark.parametrize(
    ("returncode", "stderr", "expected_status"),
    [
        (0, "", "success"),
        (1, "Conversion failed", "error"),
    ],
)
def test_process_prompt(
    monkeypatch,
    tmp_path,
    returncode,
    stderr,
    expected_status,
):
    """Проверяет успешное и ошибочное преобразование."""
    result = SimpleNamespace(
        returncode=returncode,
        stderr=stderr,
    )

    monkeypatch.setattr(
        api,
        "run_conversion",
        lambda uid, parameter: result,
    )

    monkeypatch.setattr(
        api.storage,
        "data_dir",
        Path(tmp_path),
    )

    response, status, error, duration = api.process_prompt(
        101,
        "example1.html",
        "0",
    )

    assert status == expected_status
    assert isinstance(duration, int)
    assert duration >= 0

    if returncode == 0:
        assert response == str(tmp_path / "prompt_101.docx")
        assert error == ""
    else:
        assert response == ""
        assert error == stderr
