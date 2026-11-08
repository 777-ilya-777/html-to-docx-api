from pathlib import Path
from types import SimpleNamespace

import pytest

from src import api


@pytest.mark.parametrize(
    ("returncode", "stderr", "expected_status", "expected_error"),
    [
        (0, "", "success", ""),
        (1, "Conversion failed", "error", "Conversion failed"),
    ],
)
def test_process_prompt(
    monkeypatch, tmp_path, returncode, stderr, expected_status, expected_error
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

    expected_responses = {
        "success": str(tmp_path / "prompt_101.docx"),
        "error": "",
    }

    assert (status, error) == (expected_status, expected_error)
    assert isinstance(duration, int)
    assert duration >= 0
    assert response == expected_responses[expected_status]