import logging
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from streamstats.errors import InvalidEventError, InvalidTimestampError
from streamstats.models import LogEvent

logger = logging.getLogger("streamstats")


@dataclass
class AnalysisResult:
    """Контейнер для хранения агрегированной статистики потока логов."""

    total_events: int
    events_by_level: dict[str, int]
    events_by_source: dict[str, int]
    top_error_sources: dict[str, int]
    start_time: datetime | None
    end_time: datetime | None
    invalid_records: int = 0


def analyze_events(
    records: Iterator[dict[str, Any]],
    skip_invalid: bool = False,
) -> AnalysisResult:
    """Выполняет однопроходную потоковую агрегацию событий без загрузки всего файла в память."""
    total_events = 0
    invalid_records = 0
    events_by_level: Counter[str] = Counter()
    events_by_source: Counter[str] = Counter()
    error_sources: Counter[str] = Counter()
    start_time: datetime | None = None
    end_time: datetime | None = None

    for record in records:
        try:
            event = LogEvent.from_dict(record)
        except (InvalidEventError, InvalidTimestampError) as error:
            if skip_invalid:
                logger.warning(f"Допущена ошибка в записи: {error}")
                invalid_records += 1
                continue
            raise

        total_events += 1
        events_by_level[event.level] += 1
        events_by_source[event.source] += 1

        if event.level in {"ERROR", "CRITICAL"}:
            error_sources[event.source] += 1

        if start_time is None:
            start_time = event.timestamp
            end_time = event.timestamp
        else:
            start_time = min(start_time, event.timestamp)
            end_time = max(end_time, event.timestamp)

    sorted_errors = sorted(
        error_sources.items(),
        key=lambda item: (-item[1], item[0]),
    )[:5]

    return AnalysisResult(
        total_events=total_events,
        events_by_level=dict(events_by_level),
        events_by_source=dict(events_by_source),
        top_error_sources=dict(sorted_errors),
        start_time=start_time,
        end_time=end_time,
        invalid_records=invalid_records,
    )


def filter_records(
    records: Iterator[dict[str, Any]],
    level: str | None = None,
    source: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> Iterator[dict[str, Any]]:
    """Ленивый фильтр сырых записей по уровню, источнику и времени."""
    for record in records:
        if level is not None and record.get("level") != level:
            continue
        if source is not None and record.get("source") != source:
            continue
        if since is not None or until is not None:
            raw_ts = record.get("timestamp")
            if isinstance(raw_ts, str):
                try:
                    normalized = raw_ts[:-1] + "+00:00" if raw_ts.endswith("Z") else raw_ts
                    ts = datetime.fromisoformat(normalized)
                except ValueError:
                    # Если дата битая, пропускаем её дальше — с ней разберётся analyze_events
                    yield record
                    continue
                if since is not None and ts < since:
                    continue
                if until is not None and ts > until:
                    continue
        yield record

