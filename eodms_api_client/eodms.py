import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from json import dumps, loads
from time import sleep

from requests.exceptions import ConnectionError
from tqdm.auto import tqdm

from .auth import create_session
from .geo import metadata_to_gdf, transform_metadata_geometry
from .params import generate_meta_keys, validate_query_args

EODMS_DEFAULT_MAXRESULTS = 150
EODMS_SUBMIT_HARDLIMIT = 100
EODMS_REST_BASE = 'https://www.eodms-sgdot.nrcan-rncan.gc.ca/wes/rapi'
EODMS_REST_SEARCH = EODMS_REST_BASE + \
    '/search?collection={collection}&query={query}' + \
    '&maxResults=%d&format=json' % EODMS_DEFAULT_MAXRESULTS
EODMS_REST_ORDER = EODMS_REST_BASE + '/order'

EODMS_COLLECTIONS = [
    'Radarsat1', 'Radarsat2', 'RCMImageProducts', 'NAPL', 'PlanetScope'
]

LOGGER = logging.getLogger('eodmsapi.main')
LOGGER.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s', '%Y-%m-%d %H:%M:%S')
ch.setFormatter(formatter)
LOGGER.addHandler(ch)

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
        self._session = create_session(username, password)
    
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
        LOGGER.debug('Validate query args')
        prepped_query = validate_query_args(kwargs, self.collection)
        LOGGER.debug('Query args validated')
        self._search_url = EODMS_REST_SEARCH.format(
            collection=self.collection, query=prepped_query
        )
        LOGGER.debug('Query sent')
        search_response = self._submit_search()
        LOGGER.debug('Query response received')
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
            LOGGER.warning('ConnectionError - HTTP %d: %s' % (r.status_code, r.reason))
            LOGGER.warning('Retrying in 3 seconds...')
            sleep(3)
            return self._submit_search()
        if r.ok:
            data = r.json()
            # the data['moreResults'] response is unreliable
            # thus, we submit another query if the number of results 
            # matches our query's maxResults value
            if data['totalResults'] == old_maxResults:
                LOGGER.warning('Number of search results (%d) equals query limit (%d)' % (
                    data['totalResults'], old_maxResults)
                )
                new_maxResults = old_maxResults + EODMS_DEFAULT_MAXRESULTS
                self._search_url = self._search_url.replace(
                    '&maxResults=%d' % old_maxResults,
                    '&maxResults=%d' % new_maxResults
                )
                return self._submit_search()
            else:
                return data
            return data

    def _fetch_metadata(self, query_response, metadata_fields,
                        target_crs=None, max_workers=4, len_timeout=5):
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
            (default: 5 seconds)

        Outputs:
          - geodataframe containing the scraped metadata_fields and polygon geometries
        '''
        if len(query_response['results']) == 0:
            LOGGER.warn('No results found')
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
        r = self._session.get(url, timeout=timeout)
        if r.ok:
            response = r.json()
            for k in keys:
                try:
                    metadata[k] = response[k]
                except KeyError:
                    metadata[k] = [
                        f[1] for f in response['metadata'] if f[0] == k
                    ][0]
            metadata['geometry'] = transform_metadata_geometry(
                response['geometry'],
                target_crs
            )
        return metadata

    def order(self, record_ids):
        '''
        Submit an order to EODMS using record ID numbers retrieved from a search query

        Inputs:
          - record_ids: list of record ID numbers to order

        Outputs:
          - item_ids: list of EODMS ordering system ID numbers for later downloading
        '''
        order_ids = []
        if not isinstance(record_ids, (list, tuple)):
            record_ids = [record_ids]
        if len(record_ids) < 1:
            LOGGER.warning('No records passed to order submission')
            return order_ids
        if len(record_ids) > EODMS_SUBMIT_HARDLIMIT:
            LOGGER.warning('Number of requested images exceeds limit (%d)' % EODMS_SUBMIT_HARDLIMIT)
        LOGGER.info('Submitting order for %d item%s' % (
            len(record_ids),
            's' if len(record_ids) != 1 else ''
        ))
        item_ids = []
        idx = 0
        while idx < len(record_ids):
            data = dumps({
                'destinations': [],
                'items': [
                    {
                        'collectionId': self.collection,
                        'recordId': record_id
                    }
                    for record_id in record_ids[idx:idx+EODMS_SUBMIT_HARDLIMIT]
                ]
            })
            r = self._session.post(EODMS_REST_ORDER, data=data)
            if r.ok:
                response = r.json()
                item_ids.extend(list(set([int(item['itemId']) for item in response['items']])))
            else:
                LOGGER.error('Problem submitting order - HTTP-%s: %s' % (r.status_code, r.reason))
                exit()
            idx += EODMS_SUBMIT_HARDLIMIT
        return item_ids

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
        # remote filesize
        manifest_key = list(item['manifest'].keys()).pop()
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
                    LOGGER.info('Local file exists: %s' % local)
                    continue
                # otherwise, delete the incomplete/malformed local file and redownload
                else:
                    LOGGER.warn(
                        'Filesize mismatch with %s. Re-downloading...' % os.path.basename(local)
                    )
                    os.remove(local)
            # use streamed download so we can wrap nicely with tqdm
            with self._session.get(remote, stream=True) as stream:
                with open(local, 'wb') as pipe:
                    with tqdm.wrapattr(
                        pipe,
                        method='write',
                        miniters=1,
                        total=expected_size,
                        desc=os.path.basename(local)
                    ) as file_out:
                        for chunk in stream.iter_content(chunk_size=1024):
                            file_out.write(chunk)
        return local_items

    def download(self, item_ids, output_location='.'):
        '''
        Unfortunately, there seems to be no way to query the EODMS API by OrderID, so we have to
        construct a query including the provided ItemID values

        Appears that the endpoint has a hard limit of 100 results, so need to be fancy if more
        than 100 ItemIDs are passed
        '''
        local_files = []
        os.makedirs(output_location, exist_ok=True)
        if not isinstance(item_ids, (list, tuple)):
            item_ids = [item_ids]
        n_items = len(item_ids)
        if n_items < 1:
            LOGGER.warning('No records passed to order submission')
            return local_files
        LOGGER.info('Checking statuses of %d item%s' % (
            n_items,
            's' if n_items != 1 else ''
        ))
        response = {
            'items': []
        }
        # need to submit 1 API request per imageId to check downloadable status
        status_updates = [
            EODMS_REST_ORDER + '?itemId=%s' % itemId for itemId
            in item_ids
        ]
        for update_request in status_updates:
            r = self._session.get(update_request)
            if r.ok:
                response['items'].extend(r.json()['items'])
            else:
                LOGGER.error('Problem getting item statuses - HTTP-%s: %s' % (
                    r.status_code, r.reason)
                )
        # Get a list of the ready-to-download items with their filesizes
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
            LOGGER.info('%d/%d items exist locally after latest download' % (
                n_missing_but_ready + n_already_have,
                n_items
            ))
        else:
            # If we already have everything, do nothing
            local_files = to_download
            LOGGER.info('No further action taken')
        return local_files

class EODMSHTMLFilter(HTMLParser):
    '''
    Custom HTML parser for EODMS API item status responses

    Stolen from stackoverflow user FrBrGeorge: https://stackoverflow.com/a/55825140
    '''
    text = ""
    def handle_data(self, data):
        self.text += data
