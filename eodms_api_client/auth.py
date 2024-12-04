import os
from getpass import getpass
from json import JSONDecodeError, load, dump
from netrc import netrc

from requests import Session, post, get
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
EODMS_DDS_HOSTNAME = 'https://www.eodms-sgdot.nrcan-rncan.gc.ca'

def create_session(username=None, password=None):
    '''
    Create a persistent session object for the EODMS REST API using the given username and 
    password. If neither is provided, attempt to use the .netrc file and fallback to console
    entry as a last-resort

    Inputs:
      - username: EODMS username
      - password: EODMS password
    
    Outputs:
      - session: requests.Session object for the EODMS REST API
    '''
    if username is None and password is None:
        if os.name == 'posix':
            netrc_file = os.path.join(os.path.expanduser('~'), '.netrc')
        elif os.name == 'nt':
            netrc_file = os.path.join(os.path.expanduser('~'), '_netrc')
            if not os.path.exists(netrc_file):
                netrc_file = os.path.join(os.path.expanduser('~'), '.netrc')
                if not os.path.exists(netrc_file):
                    raise FileNotFoundError('Cannot locate netrc file in expected location: %s' % os.path.expanduser('~'))
        else:
            raise NotImplementedError('Unsupported OS: %s' % os.name)
        try:
            hosts = netrc(netrc_file).hosts
            try:
                username, _, password = hosts.get(EODMS_HOSTNAME)
            except TypeError as no_eodms_host_defined:
                raise ValueError('Cannot locate credentials for EODMS server. Check your netrc file') from no_eodms_host_defined
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


def acquire_token(username=None, password=None):
    '''
    Auth method for new system. If neither username/password is provided, attempt to use 
    the .netrc file and fallback to console entry as a last-resort

    Inputs:
      - username: EODMS username
      - password: EODMS password
    
    Outputs:
      - access_token: valid API token for requesting granule downloads through EODMS DDS
    '''
    # if not provided, use the existing functions instead of copy-pasting code
    if username is None or password is None:
        with create_session() as session:
            username = session.auth.username
            password = session.auth.password
    # token stuff
    # how I understand it:
    # if local token exists, login with user/pass, if 429 then refresh tokens and save to local, if 200 then save tokens and return access_token
    # if no local token, login with user/pass, SHOULD BE 200 then save tokens to local and return access_token
    token_file = os.path.join(os.path.expanduser('~'), '.eodms', 'aaa_auth', 'login.json')
    if os.path.exists(token_file):
        try:
            with open(token_file) as login_json:
                login_data = load(login_json)
            access_token = login_data['access_token']
            refresh_token = login_data['refresh_token']
        except (KeyError, JSONDecodeError):
            pass #TODO: do something smart   
    else:
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
    # regardless if local tokenfile exists or not, we need to login with user/pass (with a POST, interestingly)
    aaa_login_url = f"{EODMS_DDS_HOSTNAME}/aaa/v1/login"
    login_req = post(
        aaa_login_url,
        json={
            "grant_type": "password",
            "username": username,
            "password": password
        }
    )
    # essentially check for http-200
    if login_req.ok:
        # get the response and create/overwrite local token file
        try:
            login_resp = login_req.json()
        except JSONDecodeError:
            print("JSON Decode Error with response from POST:%r: %s" % (aaa_login_url, login_req.text))
            exit()
        with open(token_file, "w") as f:
            dump(login_resp, f)
        access_token = login_resp['access_token']
    # this seems to be the "you need to refresh your token" error code since they probably can't use 401 here?
    elif login_req.status_code == 429:
        aaa_refresh_url = f"{EODMS_DDS_HOSTNAME}/aaa/v1/refresh"
        refresh_req = get(
            aaa_refresh_url,
            headers={"Authorization": f"Bearer {refresh_token}"}
        )
        if refresh_req.ok:
            try:
                refresh_resp = refresh_req.json()
            except JSONDecodeError:
                print("JSON Decode Error with response from POST:%r: %s" % (aaa_refresh_url, refresh_req.text))
                exit()
            # overwrite local file with new tokens
            with open(token_file, "w") as f:
                dump(refresh_resp, f)         
            access_token = refresh_resp['access_token']
    else:
        print("Could not retrieve DDS access token from EODMS")
        return None
    # return just the access token since we don't appear to need the refresh
    # token outside regenerating access_tokens
    return access_token
