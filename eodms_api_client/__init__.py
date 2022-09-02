__name__ = 'eodms_api_client'
__version__ = '1.2.4'

import logging

from .eodms import EodmsAPI

logging.basicConfig(
    format='{asctime} | {name:<15s} | {levelname:<8s} | {message}',
    datefmt='%Y-%m-%d %H:%M:%S',
    style='{',
    level=logging.INFO
)
