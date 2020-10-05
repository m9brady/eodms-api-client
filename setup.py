from setuptools import find_packages, setup

with open('eodms_api_client/__init__.py') as f:
    version = [line.strip().split('= ')[-1][1:-1] for line in f.readlines() if line.startswith('__version__')].pop()

setup(
    name='eodms_api_client',
    version=version,
    description='Tool for querying and submitting image orders to Natural Resources Canada\'s Earth Observation Data Management System (EODMS)',
    packages=find_packages(exclude=[''])
    entry_points='''
    [console_scripts]
    eodmsapi=eodms_api_client.cli:cli
    '''
)