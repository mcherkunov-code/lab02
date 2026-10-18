import json
import subprocess
import sys
from pathlib import Path

import pytest

from streamstats.analysis import analyze_events
from streamstats.errors import InvalidEventError
from streamstats.parsers import parse_csv, parse_jsonl
from streamstats.report import render_report


def test_parsers_csv_and_jsonl(tmp_path: Path) -> None:
    '''Unit-тест парсеров CSV и JSONL на корректное чтение полей.'''
    csv_file = tmp_path / 'test.csv'
    csv_file.write_text(
        'timestamp,level,source,message\n'
        '2026-10-18T12:00:00+03:00,INFO,auth,login ok\n',
        encoding='utf-8',
    )
    records_csv = list(parse_csv(csv_file))
    assert len(records_csv) == 1
    assert records_csv[0]['source'] == 'auth'

    jsonl_file = tmp_path / 'test.jsonl'
    jsonl_file.write_text(
        '{"timestamp": "2026-10-18T12:00:00+03:00", "level": "DEBUG", "source": "api", "message": "ping"}\n',
        encoding='utf-8',
    )
    records_jsonl = list(parse_jsonl(jsonl_file))
    assert len(records_jsonl) == 1
    assert records_jsonl[0]['level'] == 'DEBUG'


def test_empty_file(tmp_path: Path) -> None:
    '''Тест обработки пустого файла без падений.'''
    empty_file = tmp_path / 'empty.jsonl'
    empty_file.write_text('', encoding='utf-8')

    result = analyze_events(parse_jsonl(empty_file))
    assert result.total_events == 0
    assert result.start_time is None
    assert result.end_time is None
    assert result.invalid_records == 0

    report = json.loads(render_report(result))
    assert report['total_events'] == 0
    assert report['start_time'] is None


def test_invalid_record_modes() -> None:
    '''Тест повреждённой строки: остановка по умолчанию и пропуск с флагом.'''
    bad_records = [
        {'timestamp': '2026-10-18T12:00:00+03:00', 'level': 'INFO', 'message': 'нет источника'},
        {'timestamp': '2026-10-18T12:05:00+03:00', 'level': 'ERROR', 'source': 'db', 'message': 'fail'},
    ]

    # Режим по умолчанию: должно быть возбуждено исключение
    with pytest.raises(InvalidEventError):
        analyze_events(iter(bad_records), skip_invalid=False)

    # Режим со skip_invalid: ошибка пропускается, корректная запись учитывается
    result = analyze_events(iter(bad_records), skip_invalid=True)
    assert result.total_events == 1
    assert result.invalid_records == 1
    assert result.events_by_level['ERROR'] == 1


def test_multiple_files_aggregation(tmp_path: Path) -> None:
    '''Тест объединения статистики нескольких файлов в один поток.'''
    file1 = tmp_path / 'f1.jsonl'
    file1.write_text(
        '{"timestamp": "2026-10-18T10:00:00+03:00", "level": "INFO", "source": "s1", "message": "m1"}\n',
        encoding='utf-8',
    )
    file2 = tmp_path / 'f2.jsonl'
    file2.write_text(
        '{"timestamp": "2026-10-18T11:00:00+03:00", "level": "ERROR", "source": "s2", "message": "m2"}\n',
        encoding='utf-8',
    )

    def combined_stream():
        yield from parse_jsonl(file1)
        yield from parse_jsonl(file2)

    result = analyze_events(combined_stream())
    assert result.total_events == 2
    assert result.events_by_source == {'s1': 1, 's2': 1}
    assert result.top_error_sources == {'s2': 1}


def test_unicode_support(tmp_path: Path) -> None:
    '''Тест корректного сохранения кириллицы в данных и итоговом отчёте.'''
    records = [
        {
            'timestamp': '2026-10-18T12:00:00+03:00',
            'level': 'INFO',
            'source': 'сервис_авторизации',
            'message': 'Пользователь вошёл в систему',
        }
    ]
    result = analyze_events(iter(records))
    report_text = render_report(result)

    # Проверяем, что кириллица не превратилась в \u0441...
    assert 'сервис_авторизации' in report_text
    assert 'Пользователь' not in report_text  # сообщения в отчет не попадают, но парсер их принимает


def test_cli_integration(tmp_path: Path) -> None:
    '''Интеграционный тест вызова CLI через subprocess с кодами 0 и 2.'''
    log_file = tmp_path / 'input.jsonl'
    log_file.write_text(
        '{"timestamp": "2026-10-18T12:00:00+03:00", "level": "INFO", "source": "app", "message": "ok"}\n'
        '{"bad": "data"}\n',
        encoding='utf-8',
    )
    out_file = tmp_path / 'report.json'

    # 1. Запуск без флага должен вернуть код 2
    cmd_fail = [sys.executable, '-m', 'streamstats', 'analyze', str(log_file)]
    res_fail = subprocess.run(cmd_fail, check=False, capture_output=True, text=True)
    assert res_fail.returncode == 2

    # 2. Запуск со --skip-invalid и --output должен вернуть код 0
    cmd_ok = [
        sys.executable,
        '-m',
        'streamstats',
        'analyze',
        str(log_file),
        '--skip-invalid',
        '--output',
        str(out_file),
    ]
    res_ok = subprocess.run(cmd_ok, check=False, capture_output=True, text=True)
    assert res_ok.returncode == 0
    assert out_file.exists()

    report_data = json.loads(out_file.read_text(encoding='utf-8'))
    assert report_data['total_events'] == 1
    assert report_data['invalid_records'] == 1
