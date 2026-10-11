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