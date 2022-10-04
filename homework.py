import json
import logging
import os
import sys
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler
from typing import Dict, List

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
BASE_DIR = '/log/'

VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
formatter = '%(asctime)s - %(name)s - %(funcName)s - %(lineno)d - %(message)s'
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter(formatter))
logger.addHandler(stream_handler)
handler = RotatingFileHandler(
    BASE_DIR, maxBytes=50000000, backupCount=5, encoding='UTF-8')
logger.addHandler(handler)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logger.info(f'Начали отправку сообщения "{message}" в Telegram')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Сообщение "{message}" отправлено в Telegram')
        return True
    except telegram.error.TelegramError as error:
        logger.error(f'Ошибка: {error}')
        return False


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    api_answer = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': params
    }
    logger.info('Начали запрос к API {url}, {headers}, {params}'.format(
        **api_answer))
    try:
        response = requests.get(**api_answer)
        if response.status_code != HTTPStatus.OK:
            raise exceptions.NonStatusCodeError(
                f'{response.status_code}, {response.reason}'
                f'{response.raise_for_status()}'
            )
        logger.info('Соединение с сервером установлено!')
        return response.json()
    except json.decoder.JSONDecodeError:
        raise exceptions.JSonDecoderError('Ошибка преобразования в JSON')
    except requests.RequestException as request_error:
        raise exceptions.WrongStatusCodeError(
            f'Код ответа API (RequestException): {request_error}'
        )
    except Exception:
        raise ConnectionError(
            '(Exception) {url}, {headers}, {params}'.format(**api_answer)
        )


def check_response(response):
    """Проверяет ответ API на корректность."""
    logger.info('Начали проверку ответа API')
    if not isinstance(response, Dict):
        raise TypeError('Ответ API не является словарем')
    if 'homeworks' not in response:
        raise exceptions.EmptyAnswerFromAPI('Пустой ответ от API')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, List):
        raise TypeError('homeworks не является списком')
    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('homework_name отсутствует в словаре homework')
    homework_status = homework.get('status')
    if homework_status not in VERDICTS:
        raise ValueError('status отсутствует в словаре VERDICTS')
    return 'Изменился статус проверки работы "{homework_name}".' \
           ' {verdict}'.format(
               homework_name=homework.get('homework_name'),
               verdict=VERDICTS.get(homework_status)
           )


def check_tokens():
    """Проверяет доступность переменных окружения."""
    token_list = (
        ('Токен практикума', PRACTICUM_TOKEN),
        ('Токен телеграм-бота', TELEGRAM_TOKEN),
        ('Чат ID', TELEGRAM_CHAT_ID),
    )
    answer = True
    for name, token in token_list:
        if not token:
            logger.critical(f'{name} не указан')
            answer = False
    return answer


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise exceptions.NonTokenError('Отсутствует токен(ы)')
    logger.critical('Отсутствует токен(ы)')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    current_report = {}
    prev_report = {}
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if response:
                first_homework = homeworks[0]
                current_report['output'] = parse_status(first_homework)
            else:
                current_report['output'] = 'Нет новых статусов'
            if current_report != prev_report:
                send_message(bot, current_report['output'])
                if True:
                    prev_report = current_report.copy()
                    current_timestamp = response.get(
                        'current_date', current_timestamp)
            else:
                logger.info('Нет новых статусов')
        except exceptions.EmptyAnswerFromAPI as error:
            message = f'Пустой ответ от API {error}'
            logger.error(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            current_report['output'] = message
            if current_report != prev_report:
                send_message(bot, current_report['output'])
                prev_report = current_report.copy()
            logger.error(message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
