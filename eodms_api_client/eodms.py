import logging
import re
from concurrent.futures import ThreadPoolExecutor
from json import dumps, loads

from tqdm.auto import tqdm

from .auth import create_session
from .geo import metadata_to_gdf, transform_metadata_geometry
from .params import generate_meta_keys, validate_query_args

EODMS_DEFAULT_MAXRESULTS = 150
EODMS_REST_BASE = 'https://www.eodms-sgdot.nrcan-rncan.gc.ca/wes/rapi'
EODMS_REST_SEARCH = EODMS_REST_BASE + \
    '/search?collection={collection}&query={query}' + \
    '&maxResults=%d&format=json' % EODMS_DEFAULT_MAXRESULTS
EODMS_REST_ORDER = EODMS_REST_BASE + '/order'

LOGGER = logging.getLogger('eodmsapi.main')
LOGGER.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s', '%Y-%m-%d %H:%M:%S')
ch.setFormatter(formatter)
LOGGER.addHandler(ch)

class EodmsAPI():
    def __init__(self, collection, username=None, password=None):
        '''
        Entry-point for accessing the EODMS REST API

        Inputs:
          - collection: The EODMS Collection to which queries and orders will be sent
          - username: EODMS account username, leave blank to use .netrc (if available)
          - password: EODMS account password, leave blank to use .netrc (if available)
        '''
        self.collection = collection
        self._session = create_session(username, password)
    
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
          - None: this method uses the self.search_url attribute

        Outputs:
          - data: the search-query response JSON from the EODMS REST API
        '''
        old_maxResults = int(re.search(r'&maxResults=([\d*]+)', self._search_url).group(1))
        r = self._session.get(self._search_url)
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
                self.search_url = self.search_url.replace(
                    '&maxResults=%d' % old_maxResults,
                    '&maxResults=%d' % new_maxResults
                )
                self._submit_search()
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
        return metadata_to_gdf(results, target_crs=target_crs)
        
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
          - order_ids: list of EODMS ordering system ID numbers to keep track of
            order statuses
        '''
        order_ids = []
        if not isinstance(record_ids, (list, tuple)):
            record_ids = [record_ids]
        if len(record_ids) < 1:
            LOGGER.warning('No records passed to order submission')
            return order_ids
        LOGGER.info('Submitting order for %d items' % len(record_ids))
        data = dumps({
            'destinations': [],
            'items': [
                {
                    'collectionId': self.collection,
                    'recordId': record_id
                }
                for record_id in record_ids
            ]
        })
        r = self._session.post(EODMS_REST_ORDER, data=data)
        if r.ok:
            response = r.json()
            order_ids = list(set([item['orderId'] for item in response['items']]))
        else:
            LOGGER.error('Problem submitting order - HTTP-%s: %s' % (r.status_code, r.reason))
        return order_ids
