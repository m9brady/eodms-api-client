import os
from datetime import datetime, timedelta
from getpass import getpass
from json import JSONDecodeError, dump, load
from netrc import netrc

from requests import Session, get, post
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
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
    Auth method for new DDS system. If neither username/password is provided, attempt to use 
    the .netrc file and fallback to console entry as a last-resort

    Inputs:
      - username: EODMS username
      - password: EODMS password
    
    Outputs:
      - access_token: valid API token for requesting granule downloads through EODMS DDS
    '''
    # if not provided, use the existing functions instead of copy-pasting code
    if username is None and password is None:
        with create_session() as session:
            username = session.auth.username
            password = session.auth.password
    elif username is None and password is not None:
        username = input("Enter EODMS username: ")
    elif username is not None and password is None:
        password = getpass("Enter EODMS password: ")
    # token stuff
    aaa_login_url = f"{EODMS_DDS_HOSTNAME}/aaa/v1/login"
    aaa_refresh_url = f"{EODMS_DDS_HOSTNAME}/aaa/v1/refresh"
    # TODO: Find out if EODMS DDS token system uses UTC or local time
    now = datetime.now()
    token_file = os.path.join(os.path.expanduser('~'), '.eodms', 'aaa_creds.json')
    if os.path.exists(token_file):
        try:
            with open(token_file) as login_json:
                login_data = load(login_json)
            access_token = login_data['access_token']
            try:
                access_expiry = datetime.strptime(login_data['access_expiration'], '%Y-%m-%dT%H:%M:%S.%f')
            # when the entries are set to "null"
            except (TypeError, ValueError):
                return access_token
            refresh_token = login_data['refresh_token']
            refresh_expiry = datetime.strptime(login_data['refresh_expiration'], '%Y-%m-%dT%H:%M:%S.%f')
        except (KeyError, JSONDecodeError):
            # if there is no access/refresh token in the local file, raise it to user's attention
            raise ValueError("Contents of DDS authorization file %r are malformed/corrupt. Please review this file for errors." % token_file)
    else:
        # Scenario A: no existing login credentials
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        # need to use login api
        login_req = post(
           aaa_login_url,
            json={
                "grant_type": "password",
                "username": username,
                "password": password
            }
        )
        if login_req.ok:
            try:
                login_resp = login_req.json()
            except JSONDecodeError:
                raise HTTPError("JSON Decode Error with response from POST:%r: %s" % (aaa_login_url, login_req.text))
            # convert the response data from seconds to time-aware and name the entries to match NRCAN repo
            login_resp['access_expiration'] = (now + timedelta(seconds=login_resp.pop('expires_in'))).isoformat()
            login_resp['refresh_expiration'] = (now + timedelta(seconds=login_resp.pop('refresh_token_expires_in'))).isoformat()
            with open(token_file, "w") as f:
                dump(login_resp, f)
            access_token = login_resp['access_token']
            # return just the access token since we don't appear to need the refresh
            # token outside regenerating access_tokens
            return access_token
        else:
            raise HTTPError("Problem encountered when retrieving first-ever DDS credentials: HTTP-%d: %s" % (login_req.status_code, login_req.reason))
    # since the token file exists locally, we check if the access token and refresh token have expired
    # Scenario B: Access token expired but Refresh token valid, we use the refresh api
    if access_expiry <= now and refresh_expiry > now:
        refresh_req = get(
            aaa_refresh_url,
            headers={"Authorization": f"Bearer {refresh_token}"}
        )
        if refresh_req.ok:
            try:
                refresh_resp = refresh_req.json()
            except JSONDecodeError:
                raise HTTPError("JSON Decode Error with response from GET:%r: %s" % (aaa_refresh_url, refresh_req.text))
            # convert the response data from seconds to time-aware and name the entries to match NRCAN repo
            refresh_resp['access_expiration'] = (now + timedelta(seconds=refresh_resp.pop('expires_in'))).isoformat()
            refresh_resp['refresh_expiration'] = (now + timedelta(seconds=refresh_resp.pop('refresh_token_expires_in'))).isoformat()
            # overwrite local file with new tokens
            with open(token_file, "w") as f:
                dump(refresh_resp, f)
            access_token = refresh_resp['access_token']
        else:
            raise HTTPError("Error refreshing DDS access token: HTTP-%d %s" % (refresh_req.status_code, refresh_req.reason))
    # Scenario C: both tokens expired, we use the login api
    elif access_expiry <= now and refresh_expiry <= now:
        login_req = post(
           aaa_login_url,
            json={
                "grant_type": "password",
                "username": username,
                "password": password
            }
        )
        if login_req.ok:
            try:
                login_resp = login_req.json()
            except JSONDecodeError:
                raise HTTPError("JSON Decode Error with response from POST:%r: %s" % (aaa_login_url, login_req.text))
            # convert the response data from seconds to time-aware and name the entries to match NRCAN repo
            login_resp['access_expiration'] = (now + timedelta(seconds=login_resp.pop('expires_in'))).isoformat()
            login_resp['refresh_expiration'] = (now + timedelta(seconds=login_resp.pop('refresh_token_expires_in'))).isoformat()
            with open(token_file, "w") as f:
                dump(login_resp, f)
            access_token = login_resp['access_token']
            # return just the access token since we don't appear to need the refresh
            # token outside regenerating access_tokens
            return access_token
        else:
            raise HTTPError("Problem encountered when retrieving first-ever DDS credentials: HTTP-%d: %s" % (login_req.status_code, login_req.reason))
    # Scenario D: access token is still valid
    elif access_expiry > now:
        return access_token
    else:
        raise UnboundLocalError("I have no idea how you hit this error. Best of luck - thoughts and prayers")
