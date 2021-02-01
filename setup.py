import re
from setuptools import find_packages, setup

with open('eodms_api_client/__init__.py') as f:
    init_txt = f.read()
name = re.search(r"__name__ = \s*'([\S.*]+)'", init_txt).group(1)
version = re.search(r"__version__ = \s*'([\d.*]+)'", init_txt).group(1)

with open('requirements.txt') as f:
    requirements = f.read().splitlines()
    
with open('README.md', 'r') as readme:
    long_description = readme.read()

setup(
    name=name,
    version=version,
    author="Mike Brady",
    author_email="mike.brady@canada.ca",
    license="MIT",
    description="Tool for querying and submitting image orders to Natural Resources Canada\'s Earth Observation Data Management System (EODMS)",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://eodms-api-client.readthedocs.io/en/latest",
    project_urls={
        "Source": "https://github.com/m9brady/eodms-api-client",
        "Tracker": "https://github.com/m9brady/eodms-api-client/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(exclude=['docs', 'tests']),
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest',
            'requests-mock',
            'rstcheck'
        ],
    },
    python_requires='~=3.6',
    entry_points='''
    [console_scripts]
    eodms=eodms_api_client.cli:cli
    '''
)
