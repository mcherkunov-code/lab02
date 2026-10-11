class StreamStatsError(Exception):
    '''Базовое исключение для всех ошибок пакета streamstats.'''

    pass


class UnsupportedFormatError(StreamStatsError):
    '''Возбуждается, если передан неподдерживаемый формат файла (не csv и не jsonl).'''

    pass


class InvalidEventError(StreamStatsError):
    '''Возбуждается, если в событии отсутствуют обязательные поля или они некорректны.'''

    pass


class InvalidTimestampError(StreamStatsError):
    '''Возбуждается, если время события не соответствует формату ISO 8601.'''

    pass


class CLIConfigError(StreamStatsError):
    '''Возбуждается при ошибках настройки параметров командной строки.'''

    pass
