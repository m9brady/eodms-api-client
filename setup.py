import re
from setuptools import find_packages, setup

with open('eodms_api_client/__init__.py') as f:
    init_txt = f.read()
name = re.search(r"__name__ = \s*'([\S.*]+)'", init_txt).group(1)
version = re.search(r"__version__ = \s*'([\d.*]+)'", init_txt).group(1)

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name=name,
    version=version,
    description='Tool for querying and submitting image orders to Natural Resources Canada\'s Earth Observation Data Management System (EODMS)',
    packages=find_packages(exclude=['docs']),
    install_requires=requirements,
    python_requires='~=3.6',
    entry_points='''
    [console_scripts]
    eodms=eodms_api_client.cli:cli
    '''
)
