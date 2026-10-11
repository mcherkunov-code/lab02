from dataclasses import dataclass
from datetime import datetime
from typing import Any

from streamstats.errors import InvalidEventError, InvalidTimestampError

# Допустимые уровни логирования
VALID_LEVELS = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}


@dataclass
class LogEvent:
    timestamp: datetime
    level: str
    source: str
    message: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'LogEvent':
        '''Создает и валидирует событие из словаря.'''
        required_keys = {'timestamp', 'level', 'source', 'message'}
        actual_keys = set(data.keys())

        # Проверка наличия обязательных полей
        if not required_keys.issubset(actual_keys):
            missing = required_keys - actual_keys
            raise InvalidEventError(f"Отсутствуют обязательные поля: {missing}")

        # Валидация времени (ISO 8601)
        raw_timestamp = str(data['timestamp'])
        try:
            parsed_timestamp = datetime.fromisoformat(raw_timestamp)
        except (ValueError, TypeError) as error:
            raise InvalidTimestampError(
                f"Неверный формат времени: {raw_timestamp}"
            ) from error

        # Валидация уровня
        level = data['level']
        if level not in VALID_LEVELS:
            raise InvalidEventError(f"Недопустимый уровень логирования: {level}")

        # Валидация источника
        source = data['source']
        if not isinstance(source, str) or not source.strip():
            raise InvalidEventError('Поле source должно быть непустой строкой')

        # Валидация сообщения
        message = data['message']
        if not isinstance(message, str):
            raise InvalidEventError('Поле message должно быть строкой')

        return cls(
            timestamp=parsed_timestamp,
            level=level,
            source=source,
            message=message,
        )