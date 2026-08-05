from pathlib import Path

import pytest

from app.services.dataset_file_import_service import (
    DatasetFileValidationError,
    _inspect_csv,
    _validated_file_name,
)


def test_file_name_rejects_path_traversal() -> None:
    with pytest.raises(DatasetFileValidationError):
        _validated_file_name("../dados.csv")


def test_inspect_csv_supports_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "dados.csv"
    path.write_bytes("nome,valor\nJoão,10\n".encode("utf-8-sig"))
    headers, count, delimiter, encoding = _inspect_csv(path)
    assert headers == ["nome", "valor"]
    assert count == 1
    assert delimiter == ","
    assert encoding == "utf-8-sig"


def test_inspect_csv_rejects_inconsistent_rows(tmp_path: Path) -> None:
    path = tmp_path / "dados.csv"
    path.write_text("a,b\n1\n", encoding="utf-8")
    with pytest.raises(DatasetFileValidationError, match="linha 2"):
        _inspect_csv(path)
