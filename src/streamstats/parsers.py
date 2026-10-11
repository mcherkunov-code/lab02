import csv
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from streamstats.errors import UnsupportedFormatError


def parse_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Построчно читает JSONL-файл и возвращает словари событий."""
    with Path(path).open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            record: dict[str, Any] = json.loads(line)
            yield record


def parse_csv(path: Path) -> Iterator[dict[str, Any]]:
    """Построчно читает CSV-файл и возвращает словари событий."""
    with Path(path).open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            yield dict(row)


def get_parser(path: str | Path) -> Iterator[dict[str, Any]]:
    """Определяет формат файла по расширению и запускает соответствующий парсер."""
    file_path = Path(path)
    extension = file_path.suffix.lower()

    if extension == ".jsonl":
        return parse_jsonl(file_path)
    if extension == ".csv":
        return parse_csv(file_path)

    raise UnsupportedFormatError(
        f"Неподдерживаемый формат файла: '{extension}'. Допустимы только .csv и .jsonl"
    )
