from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from streamstats.errors import InvalidEventError, InvalidTimestampError
from streamstats.models import LogEvent


@dataclass
class AnalysisResult:
    '''Контейнер для хранения агрегированной статистики потока логов.'''

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
    '''Выполняет однопроходную потоковую агрегацию событий без загрузки всего файла в память.'''
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
        except (InvalidEventError, InvalidTimestampError):
            if skip_invalid:
                invalid_records += 1
                continue
            raise

        total_events += 1
        events_by_level[event.level] += 1
        events_by_source[event.source] += 1

        if event.level in {'ERROR', 'CRITICAL'}:
            error_sources[event.source] += 1

        if start_time is None:
            start_time = event.timestamp
            end_time = event.timestamp
        else:
            if event.timestamp < start_time:
                start_time = event.timestamp
            if event.timestamp > end_time:
                end_time = event.timestamp

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