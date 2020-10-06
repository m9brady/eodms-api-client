import os
from getpass import getpass
from netrc import netrc

from requests import Session
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry

# establish a retry strategy with backoff
RETRY_STRAT = Retry(
    total=5, # retry a max of 5 times
    backoff_factor=2, # seconds
    status_forcelist=[500, 502, 503, 504] # only retry on these HTTP codes
)
EODMS_HOSTNAME = 'data.eodms-sgdot.nrcan-rncan.gc.ca'

def create_session(username=None, password=None):
    if username is None and password is None:
        try:
            hosts = netrc(os.path.expanduser('~') + '/.netrc').hosts
            username, _, password = hosts.get(EODMS_HOSTNAME)
        except (FileNotFoundError, TypeError):
            username = input('Enter EODMS username: ')
            password = getpass('Enter EODMS password: ')
    elif username is None and password is not None:
        username = input('Enter EODMS username: ')
    elif username is not None and password is None:
        password = getpass('Enter EODMS password: ')
    session = Session()
    session.auth = HTTPBasicAuth(username, password)
    session.mount('https://', HTTPAdapter(max_retries=RETRY_STRAT))
    return session
