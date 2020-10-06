import re
from concurrent.futures import ThreadPoolExecutor
from json import loads, dumps

from tqdm.auto import tqdm

from .auth import create_session
from .geo import metadata_to_gdf, transform_metadata_geometry
from .params import generate_meta_keys, validate_query_args

EODMS_DEFAULT_MAXRESULTS = 150
EODMS_REST_BASE = 'https://www.eodms-sgdot.nrcan-rncan.gc.ca/wes/rapi'
EODMS_REST_SEARCH = EODMS_REST_BASE + '/search?collection={collection}&query={query}&maxResults=%d&format=json' % EODMS_DEFAULT_MAXRESULTS
EODMS_REST_ORDER = EODMS_REST_BASE + '/order'

class EodmsAPI():
    def __init__(self, username, password, collection):
        self.collection = collection
        self.session = create_session(username, password)
    
    def query(self, **kwargs):
        query = validate_query_args(kwargs, self.collection)
        self.search_url = EODMS_REST_SEARCH.format(collection=self.collection, query=query)
        search_response = self.submit_search()
        meta_keys = generate_meta_keys(self.collection)
        target_crs = kwargs.get('target_crs', None)
        self.search_results = self.fetch_metadata(search_response, meta_keys, target_crs)

    def submit_search(self):
        old_maxResults = int(re.search(r'&maxResults=([\d*]+)', self.search_url).group(1))
        response = self.session.get(self.search_url)
        if response.ok:
            data = loads(response.content.decode('utf-8'))
            # the data['moreResults'] response is unreliable
            # thus, we submit another query if the number of results 
            # matches our query's maxResults value
            if data['totalResults'] == old_maxResults:
                new_maxResults = old_maxResults + EODMS_DEFAULT_MAXRESULTS
                self.search_url = self.search_url.replace(
                    '&maxResults=%d' % old_maxResults,
                    '&maxResults=%d' % new_maxResults
                )
                self.submit_search()
            else:
                return data

    def fetch_metadata(self, query_response, metadata_fields, target_crs=None, max_workers=4, len_timeout=5):
        meta_urls = [record['thisRecordUrl'] for record in query_response['results']]
        n_urls = len(meta_urls)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(
                tqdm(
                    executor.map(
                        self._fetch_single_record_metadata,
                        meta_urls,
                        [metadata_fields] * n_urls,
                        [target_crs] * n_urls
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
        metadata = {}
        r = self.session.get(url, timeout=timeout)
        if r.ok:
            response = loads(r.content.decode('utf-8'))
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

    def submit_order(self, recordIds):
        if len(recordIds) < 1:
            return []            
        data = dumps(
            {
                'destinations': [],
                'items': [
                    {
                        'collection': self.collection,
                        'recordId': recordId
                    }
                    for recordId in recordIds
                ]
            }
        )
        r = self.session.post(EODMS_REST_ORDER, data=data)
        if r.ok:
            response = loads(r.content.decode('utf-8'))
            order_ids = list(set([item['orderId'] for item in response['items']]))
        else:
            order_ids = []
        return order_ids
