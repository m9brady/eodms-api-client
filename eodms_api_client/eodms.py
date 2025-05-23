import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from json import dumps
from math import ceil
from time import sleep

from requests import get, head
from requests.exceptions import ConnectionError, HTTPError, JSONDecodeError
from tqdm.auto import tqdm

from .auth import create_session, acquire_token
from .geo import metadata_to_gdf, transform_metadata_geometry
from .params import (available_query_args, generate_meta_keys,
                     validate_query_args)

EODMS_DEFAULT_MAXRESULTS = 1000
EODMS_SUBMIT_HARDLIMIT = 50
EODMS_REST_BASE = 'https://www.eodms-sgdot.nrcan-rncan.gc.ca/wes/rapi'
EODMS_REST_SEARCH = EODMS_REST_BASE + \
    '/search?collection={collection}&query={query}' + \
    '&maxResults=%d&format=json' % EODMS_DEFAULT_MAXRESULTS
EODMS_REST_ORDER = EODMS_REST_BASE + '/order'

EODMS_DDS_BASE = 'https://www.eodms-sgdot.nrcan-rncan.gc.ca/dds/v1/item'

EODMS_COLLECTIONS = [
    'Radarsat1', 'Radarsat2', 'RCMImageProducts', 'NAPL', 'PlanetScope'
]

LOGGER = logging.getLogger('eodmsapi.main')
# suppress urllib3 warnings
logging.getLogger('urllib3').setLevel(logging.ERROR)

class EodmsAPI():
    '''
    Entry-point for accessing the EODMS REST API

    Inputs:
        - collection: The EODMS Collection to which queries and orders will be sent
        - username: EODMS account username, leave blank to use .netrc (if available)
        - password: EODMS account password, leave blank to use .netrc (if available)
    '''
    def __init__(self, collection, username=None, password=None):
        self.collection = collection
        self.available_params = available_query_args(self.collection)
        self._session = create_session(username, password)
        self._dds_access_token = None # initialize this to None since it's not needed unless we want to download
        # test the credentials
        r = self._session.get(f'{EODMS_REST_BASE}/collections/{self.collection}')
        if r.status_code == 401:
            raise ValueError('Insufficient access privileges or incorrect username and/or password')
    
    @property
    def collection(self):
        return self.__collection

    @collection.setter
    def collection(self, collection, *args, **kwargs):
        if collection not in EODMS_COLLECTIONS:
            # try to be a bit more flexible
            if collection.upper() in ['RCM']:
                self.__collection = 'RCMImageProducts'
            elif collection.upper() in ['RS1', 'RADARSAT', 'RADARSAT-1']:
                self.__collection = 'Radarsat1'
            elif collection.upper() in ['RS2', 'RADARSAT-2']:
                self.__collection = 'Radarsat2'
            elif collection.upper() in ['PLANET']:
                self.__collection = 'PlanetScope'
            else:
                raise ValueError('Unrecognized EODMS collection: "%s" - Must be one of [%s]' % (
                    collection, ', '.join(EODMS_COLLECTIONS)
                ))
        else:
            self.__collection = collection
        # reset the available params based on new collection
        self.available_params = available_query_args(self.__collection)
        return

    def query(self, **kwargs):
        '''
        Submit a query to EODMS and save the results as a geodataframe in a class 
        attribute
        
        Inputs:
          - kwargs: Any number of keyword arguments that will be validated based on
            the EODMS collection being queried

        Outputs:
          - self.results: A class attribute containing a geodataframe with
            the returned query results
        '''
        if bool(kwargs.get('debug', False)):
            LOGGER.setLevel(logging.DEBUG)
        else:
            LOGGER.setLevel(logging.INFO)
        LOGGER.debug('Validate query args')
        prepped_query = validate_query_args(kwargs, self.collection)
        LOGGER.debug('Query args validated')
        self._search_url = EODMS_REST_SEARCH.format(
            collection=self.collection, query=prepped_query
        )
        LOGGER.debug('Query sent: %s' % self._search_url)
        search_response = self._submit_search()
        n_results = search_response['hitCount']
        LOGGER.debug('Query response received (%d result%s)' % (n_results, '' if n_results == 1 else 's'))
        meta_keys = generate_meta_keys(self.collection)
        target_crs = kwargs.get('target_crs', None)
        LOGGER.debug('Generate result dataframe')
        self.results = self._fetch_metadata(search_response, meta_keys, target_crs)
        LOGGER.debug('Result dataframe ready')

    def _submit_search(self):
        '''
        Submit a search query to the desired EODMS collection

        Since there may be instances where the default maxResults is greater than 150,
        this method should recursively call itself until the correct number of results
        is retrieved

        Inputs:
          - None: this method uses the self._search_url attribute

        Outputs:
          - data: the search-query response JSON from the EODMS REST API
        '''
        old_maxResults = int(re.search(r'&maxResults=([\d*]+)', self._search_url).group(1))
        try:
            r = self._session.get(self._search_url)
        # some GETs are returning 104 ECONNRESET
        # - possibly due to geometry vertex count (failed with 734 but 73 was fine)
        except ConnectionError:
            LOGGER.warning('ConnectionError Encountered! Retrying in 3 seconds...')
            sleep(3)
            return self._submit_search()
        if r.ok:
            # add check for API being down but still returning HTTP:200
            if 'Thanks for your patience' in r.text:
                LOGGER.error('EODMS API appears to be down. Try again later.')
                # dirty filthy not-good idea
                return {'results': []}
            data = r.json()
            # the data['moreResults'] response is unreliable
            # thus, we submit another query if the number of results 
            # matches our query's maxResults value
            if data['totalResults'] == old_maxResults:
                LOGGER.warning('Number of search results (%d) equals query limit (%d)' % (
                    data['totalResults'], old_maxResults)
                )
                new_maxResults = old_maxResults + EODMS_DEFAULT_MAXRESULTS
                LOGGER.info('Increasing query limit to %d and requerying...' % new_maxResults)
                self._search_url = self._search_url.replace(
                    '&maxResults=%d' % old_maxResults,
                    '&maxResults=%d' % new_maxResults
                )
                return self._submit_search()
            else:
                return data

    def _fetch_metadata(self, query_response, metadata_fields,
                        target_crs=None, max_workers=4, len_timeout=20):
        '''
        Since the search-query response from the EODMS REST API does not return
        much useful metadata about imagery, we have to submit some more requests

        Inputs:
          - query_response: the response JSON from _submit_search()
          - metadata_fields: the metadata that will be scraped for each record. Is partially
            dependent on the collection being queried
          - target_crs: the desired projection of the image footprint polygons (default: WGS84)
          - max_workers: the number of threads to use in the metadata fetching method (default: 4)
          - len_timeout: how long each metadata fetch should wait before timing out 
            (default: 20 seconds)

        Outputs:
          - geodataframe containing the scraped metadata_fields and polygon geometries
        '''
        if len(query_response['results']) == 0:
            LOGGER.warning('No results found')
            results = {k: [] for k in metadata_fields}
            results['geometry'] = []
        else:
            meta_urls = [record['thisRecordUrl'] for record in query_response['results']]
            n_urls = len(meta_urls)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(
                    tqdm(
                        executor.map(
                            self._fetch_single_record_metadata,
                            meta_urls,
                            [metadata_fields] * n_urls,
                            [target_crs] * n_urls,
                            [len_timeout] * n_urls
                        ),
                        desc='Fetching result metadata',
                        total=n_urls,
                        miniters=1,
                        unit='item'
                    )
                )
        return metadata_to_gdf(results, self.collection, target_crs=target_crs)
        
    def _fetch_single_record_metadata(self, url, keys, target_crs, timeout):
        '''
        Fetch a single image's metadata

        Inputs:
          - url: the given image's metadata url taken from the search-api response
          - keys: which metadata fields to scrape from the fetched response
          - target_crs: the desired projection for the footprint geometry (default: WGS84)
          - timeout: the time in seconds to wait before timing out

        Outputs:
          - metadata: dictionary containing the keys and geometry metadata for the given
            image
        '''
        metadata = {}
        r = self._session.get(url, params={'format': 'json'}, timeout=timeout)
        if r.ok:
            response = r.json()
            for k in keys:
                try:
                    metadata[k] = response[k]
                except KeyError:
                    metadata[k] = [
                        f[1] for f in response['metadata'] if f[0] == k
                    ][0]
            # UUIDs are for the DDS downloading system 
            # Showerthought: is DDS just "Data Downloading System" :thinking:
            # seems to only be valid for RCM
            if self.collection == "RCMImageProducts":
                metadata['uuid'] = [
                    item[1].split('/')[-1] for item in response['metadata']
                    if item[0] == 'Metadata Full Name'
                ][0]
            metadata['thumbnailUrl'] = response['thumbnailUrl']
            metadata['geometry'] = transform_metadata_geometry(
                response['geometry'],
                target_crs
            )
        return metadata

    def order(self, record_ids, priority='Medium'):
        '''
        Submit an order to EODMS using record ID numbers retrieved from a search query

        Inputs:
          - record_ids: list of record ID numbers to order
          - priority: Order submission priority. Must be one of ['Low', 'Medium', 'High', 'Urgent'] Default: 'Medium'

        Outputs:
          - order_ids: list of EODMS ordering system ID numbers for later downloading
        '''
        if not isinstance(record_ids, (list, tuple)):
            record_ids = [record_ids]
        if priority.capitalize() not in ['Low', 'Medium', 'High', 'Urgent']:
            raise ValueError('Unrecognized priority: %s' % priority)
        n_records = len(record_ids)
        if n_records < 1:
            LOGGER.warning('No records passed to order submission')
            return None
        if n_records > EODMS_SUBMIT_HARDLIMIT:
            LOGGER.warning('Number of requested images exceeds per-order limit (%d)' % EODMS_SUBMIT_HARDLIMIT)
            LOGGER.info('Submitting %d orders to accomodate %d items' % (
                ceil(n_records / EODMS_SUBMIT_HARDLIMIT), n_records
            ))
        else:
            LOGGER.info('Submitting order for %d item%s' % (
                n_records,
                's' if n_records != 1 else ''
            ))
        order_ids = []
        idx = 0
        while idx < n_records:
            # only submit 50 items per order
            record_subset = record_ids[idx:idx+EODMS_SUBMIT_HARDLIMIT]
            data = dumps({
                'destinations': [],
                'items': [
                    {
                        'collectionId': self.collection,
                        'recordId': str(record_id),
                        'priority': priority.capitalize(),
                        'parameters': {
                            'NOTIFICATION_EMAIL_ADDRESS': self._session.auth.username,
                            'packagingFormat': 'ZIP',

                        }
                    }
                    for record_id in record_subset
                ]
            })
            r = self._session.post(EODMS_REST_ORDER, data=data)
            if r.ok:
                LOGGER.debug('%s priority order accepted by EODMS for %d item%s' % (
                    priority, len(record_subset), 's' if len(record_subset) != 1 else '')
                )
                try:
                    response = r.json()
                    order_ids.extend(list(set([int(item['orderId']) for item in response['items']])))
                except JSONDecodeError:
                    LOGGER.error('An unexpected response has been received from EODMS API - double-check that your order has been submitted via the web interface')
                    LOGGER.error('You will likely need to get your Order ID from the EODMS Web Interface or the order-completion email')
            else:
                LOGGER.error('Problem submitting order - HTTP-%s: %s' % (r.status_code, r.reason))
                raise ConnectionError('Problem submitting order - HTTP-%s: %s' % (r.status_code, r.reason))
            idx += EODMS_SUBMIT_HARDLIMIT
        return order_ids

    def _extract_download_metadata(self, item):
        '''
        Because the download link in the response from EODMS is HTML-encoded, we have to parse out
        the actual download URL and the filesize

        Inputs:
          - item: JSON (dict) of item metadata from EODMS

        Outputs:
          - url: remote file URL
          - fsize: remote filesize in bytes
        '''
        # download url
        parser = EODMSHTMLFilter()
        parser.feed(item['destinations'][0]['stringValue'])
        url = parser.text
        # strip &file= from end of url
        # TODO: THIS IS A BANDAID FIX THAT WILL PROBABLY HAVE TO BE REMOVED LATER
        url = url.split('&file=')[0]
        manifest_key = list(item['manifest'].keys()).pop()
        manifest_hash = manifest_key.split('/')[0]
        # check that url matches manifest 
        # TODO: BANDAID FIX, REMOVE WHEN FIXED ON SERVER-SIDE
        split_url = url.split(manifest_hash)
        if not f'{manifest_hash}{split_url[-1]}' == manifest_key:
            url = f'{split_url[0]}{manifest_key}'
        # remote filesize
        fsize = int(item['manifest'][manifest_key])
        return url, fsize

    def _download_items(self, remote_items, local_items):
        '''
        Given a list of remote and local items, download the remote data if it is not already
        found locally

        Inputs:
          - remote_items: list of tuples containing (remote url, remote filesize)
          - local_items: list of local paths where data will be saved

        Outputs:
          - local_items: same as input 

        Assumptions:
          - length of remote_items and local_items must match
          - filenames in remote_items and local_items must be in sequence
        '''
        remote_urls = [f[0] for f in remote_items]
        remote_sizes = [f[1] for f in  remote_items]
        for remote, expected_size, local in zip(remote_urls, remote_sizes, local_items):
            # if we have an existing local file, check the filesize against the manifest
            if os.path.exists(local):
                # if all-good, continue to next file
                if os.stat(local).st_size == expected_size:
                    LOGGER.debug('Local file exists: %s' % local)
                    continue
                # otherwise, delete the incomplete/malformed local file and redownload
                else:
                    LOGGER.warning(
                        'Filesize mismatch with %s. Re-downloading...' % os.path.basename(local)
                    )
                    os.remove(local)
            # use streamed download so we can wrap nicely with tqdm
            with self._session.get(remote, stream=True) as stream:
                # use content-type to catch non-zipfiles
                if stream.headers['content-type'] != 'application/zip':
                    LOGGER.error(
                        'Remote file %s does not appear to be a ' % os.path.basename(remote) +\
                        'zipfile anymore (content-type: %s). ' % stream.headers['content-type'] +\
                        'You may have to resubmit your order or contact EODMS support.'
                    )
                    continue
                with open(local, 'wb') as pipe:
                    with tqdm.wrapattr(
                        pipe,
                        method='write',
                        miniters=1,
                        total=int(stream.headers['content-length']),
                        desc=os.path.basename(local)
                    ) as file_out:
                        for chunk in stream.iter_content(chunk_size=1024):
                            file_out.write(chunk)
        return local_items

    def download(self, order_ids, output_location='.'):
        '''
        Appears that the endpoint has a hard limit of 100 results, so need to be fancy if more
        than 100 items are given for an orderId

        order_ids: list of integer order numbers
        output_location: where the downloaded products will be saved to (will be created if doesn't exist yet)
        '''
        local_files = []
        LOGGER.debug('Saving to %r' % output_location)
        os.makedirs(output_location, exist_ok=True)
        if not isinstance(order_ids, (list, tuple)):
            order_ids = [order_ids]
        n_orders = len(order_ids)
        if n_orders < 1:
            LOGGER.warning('No order_ids provided - no action taken')
            return local_files
        LOGGER.info('Checking status%s of %d order%s' % (
            'es' if n_orders != 1 else '',
            n_orders,
            's' if n_orders != 1 else ''
        ))
        response = {
            'items': []
        }
        extra_stuff = {
            'maxOrders': EODMS_DEFAULT_MAXRESULTS,
            'format': 'json'
        }
        # need to submit 1 API request per orderId to check downloadable status
        status_updates = [
            EODMS_REST_ORDER + '?orderId=%d' % orderId for orderId
            in order_ids
        ]
        for update_request in status_updates:
            r = self._session.get(update_request, params=extra_stuff)
            if r.ok:
                # add check for API being down but still returning HTTP:200
                if 'Thanks for your patience' in r.text:
                    LOGGER.error('EODMS API appears to be down. Try again later.')
                    return
                # only retain items that belong to the wanted orderIds
                items = [
                    item for item in r.json()['items'] 
                    if item['orderId'] in order_ids and 
                    item not in response['items']
                ]
                response['items'].extend(items)
            else:
                LOGGER.error('Problem getting item statuses - HTTP-%s: %s' % (
                    r.status_code, r.reason)
                )
        # Get a list of the ready-to-download items with their filesizes
        n_items = len(response['items'])
        available_remote_files = [
            self._extract_download_metadata(item)
            for item in response['items'] 
            if item['status'] == 'AVAILABLE_FOR_DOWNLOAD'
        ]
        LOGGER.info('%d/%d items ready for download' % (
            len(available_remote_files),
            n_items
        ))
        to_download = [
            os.path.join(output_location, os.path.basename(f[0]))
            for f in available_remote_files
        ]
        # Establish what we already have      
        already_have = [f for f in to_download if os.path.exists(f)]
        n_already_have = len(already_have)
        LOGGER.info('%d/%d items exist locally' % (
            n_already_have,
            n_items
        ))
        if n_already_have < len(available_remote_files):
            # Download any available-on-remote-but-missing-from-local
            n_missing_but_ready = len(available_remote_files) - n_already_have
            LOGGER.info('Downloading %d remote item%s' % (
                n_missing_but_ready,
                's' if n_missing_but_ready != 1 else ''
            ))
            local_files = self._download_items(available_remote_files, to_download)
            # account for any skipped-files-due-to-wrong-filesize
            local_files = [f for f in local_files[:] if os.path.exists(f)]
            LOGGER.info('%d/%d items exist locally after latest download' % (
                len(local_files),
                n_items
            ))
        else:
            # If we already have everything, do nothing
            local_files = to_download
            LOGGER.info('No further action taken')
            return
        return local_files

    def _download_dds_item(self, uuid, output_directory):
        """
        subfunction used by download_dds to acquire datasets from EODMS DDS
        while the logging messages are useful and I want them to be INFO level, they really mess up the
        tqdm progress bars
        """
        url = f'{EODMS_DDS_BASE}/EODMS/{self.collection}/{uuid}'
        header = {"Authorization": f"Bearer {self._dds_access_token}"}
        # issue a GET to DDS to get the status of the wanted granule
        # drives me nuts that we can't re-use the self._session for this!
        # TODO: add bombproofing
        LOGGER.debug("Requesting UUID %r" % uuid)
        uuid_req = get(url, headers=header)
        if not uuid_req.ok:
            # if our token has expired, get a new one
            # TODO: race-condition if concurrent downloads do this at the same time?
            if uuid_req.status_code == 401:
                self._dds_access_token = acquire_token(
                    self._session.auth.username,
                    self._session.auth.password
                )
                header = {"Authorization": f"Bearer {self._dds_access_token}"}
                uuid_req = get(url, headers=header)
        try:
            uuid_resp = uuid_req.json()
        except JSONDecodeError:
            raise HTTPError("JSONDecodeError with UUID %r: %s" % (uuid, uuid_req.text))
        while "download_url" not in uuid_resp.keys():
            LOGGER.debug("UUID %r pending" % uuid)
            sleep(5)
            uuid_req = get(url, headers=header)
            if not uuid_req.ok:
                raise HTTPError("Problem with UUID %r: HTTP-%d (%s)" % (uuid, uuid_req.status_code, uuid_req.reason))
            try:
                uuid_resp = uuid_req.json()
            except JSONDecodeError:
                raise HTTPError("JSONDecodeError with UUID %r: %s" % (uuid, uuid_req.text))
        LOGGER.debug("UUID %r ready for download" % uuid)
        download_url = uuid_resp["download_url"]
        # retrieve granule name from url
        granule = download_url.split("?")[0].split("/")[-1]
        local = os.path.join(output_directory, granule)
        # if exists, check filesize against remote and redownload if necessary
        if os.path.exists(local):
            # this is pretty cool, credit to Kevin Ballantyne https://github.com/eodms-sgdot/py-eodms-dds/blob/e392d9800449b26fa33b076bb2f583a897d058f4/eodms_dds/dds.py#L71
            expected_size = int(head(download_url, allow_redirects=True).headers.get("Content-Length"))
            # if all-good, continue to next file
            if os.stat(local).st_size == expected_size:
                LOGGER.debug('Local file exists: %s' % local)
                return local
            # otherwise, delete the incomplete/malformed local file and redownload
            else:
                LOGGER.warning(
                    'Filesize mismatch with %s. Re-downloading...' % os.path.basename(local)
                )
                os.remove(local)
        # download to local
        os.makedirs(os.path.dirname(local), exist_ok=True)
        with open(local, 'wb') as pipe:
            with get(download_url, stream=True) as stream:
                with tqdm.wrapattr(
                    pipe,
                    method='write',
                    leave=False, # get rid of the progressbar once finished
                    miniters=1,
                    total=int(stream.headers['content-length']),
                    desc=os.path.basename(local)
                ) as file_out:
                    for chunk in stream.iter_content(chunk_size=1024):
                        file_out.write(chunk)
        return local

    def download_dds(self, uuids, output_directory, n_workers=4):
        '''
        Function that uses the new EODMS DDS system for ordering/downloading data

        Inputs:
          - uuids: list of granule UUIDs to download (not RecordId!)
          - output_directory: path to where downloads should go
          - n_workers: how many concurrent threads to use when downloading (default: 4)

        Outputs:
          - local_files: list of local datasets downloaded from EODMS
        '''
        if self.collection != "RCMImageProducts":
            raise NotImplementedError("Only RCM data is currently supported with the DDS. Current collection: %r" % self.collection)
        # ensure we have an up-to-date access_token
        if self._dds_access_token is None:
            LOGGER.debug("Acquiring DDS access token")
            self._dds_access_token = acquire_token(
                self._session.auth.username, self._session.auth.password
            )
        # distribute download tasks to threadpool
        LOGGER.info("Attempting download of %d granules across %d threads" % (len(uuids), n_workers))
        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            # use a top-level progressbar to indicate total progress
            with tqdm(position=0, total=len(uuids), unit='granule', desc='Downloading') as pbar:
                # per-download progressbars disappear once finished since they get really cluttered
                futures = [
                    executor.submit(
                        self._download_dds_item,
                        uuid,
                        output_directory
                    )
                    for uuid in uuids
                ]
                results = []
                for future in as_completed(futures):
                    pbar.update(1) # update persistent progressbar
                    results.append(future.result())
        return results


class EODMSHTMLFilter(HTMLParser):
    '''
    Custom HTML parser for EODMS API item status responses

    Stolen from stackoverflow user FrBrGeorge: https://stackoverflow.com/a/55825140
    '''
    text = ""
    def handle_data(self, data):
        self.text += data
