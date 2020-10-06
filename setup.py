import re
from setuptools import find_packages, setup

with open('eodms_api_client/__init__.py') as f:
    version = re.search(r"__version__ = \s*'([\d.*]+)'", f.read()).group(1)

setup(
    name='eodms_api_client',
    version=version,
    description='Tool for querying and submitting image orders to Natural Resources Canada\'s Earth Observation Data Management System (EODMS)',
    packages=find_packages(exclude=['']),
    entry_points='''
    [console_scripts]
    eodmsapi=eodms_api_client.cli:cli
    '''
)
