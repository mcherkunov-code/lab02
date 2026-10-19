import csv
import io
import json

from streamstats.analysis import AnalysisResult


def render_report(result: AnalysisResult) -> str:
    '''Преобразует агрегированную статистику в форматированную JSON-строку.'''
    report_dict = {
        'total_events': result.total_events,
        'events_by_level': result.events_by_level,
        'events_by_source': result.events_by_source,
        'top_error_sources': result.top_error_sources,
        'start_time': result.start_time.isoformat() if result.start_time else None,
        'end_time': result.end_time.isoformat() if result.end_time else None,
        'invalid_records': result.invalid_records,
    }

    return json.dumps(report_dict, ensure_ascii=False, indent=2)


def render_csv_report(result: AnalysisResult) -> str:
    '''Формирует CSV-отчёт из готового AnalysisResult без повторного чтения логов.'''
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator='\n')
    writer.writerow(['category', 'key', 'value'])

    writer.writerow(['summary', 'total_events', result.total_events])
    writer.writerow(['summary', 'invalid_records', result.invalid_records])
    writer.writerow([
        'summary',
        'start_time',
        result.start_time.isoformat() if result.start_time else '',
    ])
    writer.writerow([
        'summary',
        'end_time',
        result.end_time.isoformat() if result.end_time else '',
    ])

    for level, count in result.events_by_level.items():
        writer.writerow(['events_by_level', level, count])

    for source, count in result.events_by_source.items():
        writer.writerow(['events_by_source', source, count])

    for source, count in result.top_error_sources.items():
        writer.writerow(['top_error_sources', source, count])

    return buffer.getvalue()