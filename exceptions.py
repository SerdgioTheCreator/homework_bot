class NotSendMessageError(Exception):
    """Ошибка при отправке сообщения."""

    pass


class NonStatusCodeError(Exception):
    """Ошибка при получении ответа с сервера."""

    pass


class JSonDecoderError(Exception):
    """Ошибка преобразования в JSON."""

    pass


class WrongStatusCodeError(Exception):
    """Неверный ответ с сервера."""

    pass


class EmptyAnswerFromAPI(Exception):
    """Пустой ответ от API."""

    pass


class NonTokenError(Exception):
    """Отсутствуют токены чата."""

    pass
