from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from streamstats.models import LogEvent


@dataclass
class AnalysisResult:
    '''Контейнер для хранения агрегированной статистики потока логов.'''

    total_events: int
    events_by_level: dict[str, int]
    events_by_source: dict[str, int]
    start_time: datetime | None
    end_time: datetime | None


def analyze_events(records: Iterator[dict[str, Any]]) -> AnalysisResult:
    '''Выполняет однопроходную потоковую агрегацию событий без загрузки всего файла в память.'''
    total_events = 0
    events_by_level = Counter()
    events_by_source = Counter()
    start_time: datetime | None = None
    end_time: datetime | None = None

    for record in records:
        event = LogEvent.from_dict(record)
        total_events += 1
        events_by_level[event.level] += 1
        events_by_source[event.source] += 1

        if start_time is None:
            start_time = event.timestamp
            end_time = event.timestamp
        else:
            if event.timestamp < start_time:
                start_time = event.timestamp
            if event.timestamp > end_time:
                end_time = event.timestamp

    return AnalysisResult(
        total_events=total_events,
        events_by_level=dict(events_by_level),
        events_by_source=dict(events_by_source),
        start_time=start_time,
        end_time=end_time,
    )