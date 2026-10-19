import argparse
import logging
import sys
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from streamstats.analysis import analyze_events, filter_records
from streamstats.errors import StreamStatsError
from streamstats.parsers import get_parser, parse_csv, parse_jsonl
from streamstats.report import render_csv_report, render_report

logger = logging.getLogger("streamstats")


def setup_logging() -> None:
    """Настраивает логгер для вывода сообщений в stdout."""
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for old_handler in logger.handlers[:]:
        logger.removeHandler(old_handler)
        old_handler.close()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(handler)


def stream_records(
    paths: list[str],
    forced_format: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Последовательно генерирует события из нескольких файлов без загрузки в память."""
    for path_str in paths:
        path = Path(path_str)
        logger.info(f"Начинаем обработку файла: {path}")

        if forced_format == "csv":
            yield from parse_csv(path)
        elif forced_format == "jsonl":
            yield from parse_jsonl(path)
        else:
            yield from get_parser(path)


def build_parser() -> argparse.ArgumentParser:
    """Создаёт и настраивает парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="streamstats",
        description="Потоковый анализатор лог-файлов CSV и JSONL.",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Анализ одного или нескольких файлов логов.",
    )
    analyze_parser.add_argument(
        "inputs",
        nargs="+",
        metavar="INPUT",
        help="Путь к одному или нескольким файлам логов.",
    )
    analyze_parser.add_argument(
        "--format",
        choices=["csv", "jsonl"],
        default=None,
        help="Принудительный формат файла (csv или jsonl).",
    )
    analyze_parser.add_argument(
        "-o",
        "--output",
        metavar="REPORT.json",
        default=None,
        help="Путь для сохранения JSON-отчёта (по умолчанию выводится в stdout).",
    )
    analyze_parser.add_argument(
        "--skip-invalid",
        action="store_true",
        help="Пропускать повреждённые строки вместо остановки.",
    )
    analyze_parser.add_argument(
        "--level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help="Фильтр по уровню логирования.",
    )
    analyze_parser.add_argument(
        "--source",
        default=None,
        help="Фильтр по источнику события.",
    )
    analyze_parser.add_argument(
        "--since",
        default=None,
        help="Нижняя граница времени (ISO 8601).",
    )
    analyze_parser.add_argument(
        "--until",
        default=None,
        help="Верхняя граница времени (ISO 8601).",
    )

    return parser


def main() -> int:
    """Точка входа CLI: оркестрация потока, обработка аргументов и ошибок."""
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "analyze":
        try:
            records = stream_records(args.inputs, args.format)
            since_dt = datetime.fromisoformat(args.since) if args.since else None
            until_dt = datetime.fromisoformat(args.until) if args.until else None
            records = filter_records(
                records,
                level=args.level,
                source=args.source,
                since=since_dt,
                until=until_dt,
            )
            result = analyze_events(records, skip_invalid=args.skip_invalid)
            if args.output and str(args.output).endswith(".csv"):
                report_text = render_csv_report(result)
            else:
                report_text = render_report(result)

            if args.output:
                output_path = Path(args.output)
                output_path.write_text(report_text, encoding="utf-8")
                logger.info(f"Отчёт успешно сохранён в {output_path}")
            else:
                print(report_text)

            return 0
        except StreamStatsError as error:
            logger.error(f"Ошибка обработки данных: {error}")
            return 2
        except Exception as error:  # noqa: BLE001
            logger.error(f"Непредвиденная системная ошибка: {error}")
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
