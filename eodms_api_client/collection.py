from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from json import loads
from urllib.parse import quote

from tqdm.auto import tqdm

from .auth import create_session
from .geo import metadata_to_gdf, transform_metadata_geometry
from .params import convert_params, generate_meta_keys


class Collection(ABC):
    def __init__(self, *args, **kwargs):
        self.maxResults = 150
        self.meta_keys = None
        self.search_url = 'https://www.eodms-sgdot.nrcan-rncan.gc.ca/wes/rapi/search?collection={collection}&query={query}&maxResults={maxResults}&format=json'
        self.order_url = 'https://www.eodms-sgdot.nrcan-rncan.gc.ca/wes/rapi/order'
        self.session = create_session(
            kwargs.get('username', None),
            kwargs.get('password', None)
        )
    
    @abstractmethod
    def construct_query(self, query_params):
        pass

    @abstractmethod
    def submit_order(self, order_ids):
        pass

    def submit_query(self):
        response = self.session.get(self.search_url)
        if response.ok:
            data = loads(response.content.decode('utf-8'))
            # the data['moreResults'] response is unreliable
            # thus, we submit another query if the number of results 
            # matches our self.maxResults value
            if data['totalResults'] == self.maxResults:
                old_maxResults = self.maxResults
                self.maxResults += 150
                self.search_url = self.search_url.replace(
                    f'&maxResults={old_maxResults}',
                    f'&maxResults={self.maxResults}'
                )
                self.submit_query()
            else:
                fetch_metadata(data)

    def fetch_metadata(self, query_response, max_workers=4, len_timeout=5):
        meta_urls = [record['thisRecordUrl'] for record in query_response['results']]
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(
                tqdm(
                    executor.map(
                        _fetch_single_record_metadata,
                        meta_urls,
                        [len_timeout] * len(meta_urls)
                    ),
                    desc='Fetching result metadata',
                    total=len(meta_urls),
                    miniters=1,
                    unit='item'
                )
            )
        self.search_results = metadata_to_gdf(results)
        
    def _fetch_single_record_metadata(self, url, timeout):
        metadata = {}
        r = self.session.get(url, timeout=timeout)
        if r.ok:
            response = loads(r.content.decode('utf-8'))
            for k in self.meta_keys:
                try:
                    metadata[k] = response[k]
                except KeyError:
                    metadata[k] = [
                        f[1] for f in response['metadata'] if f[0] == k
                    ][0]
            metadata['geometry'] = transform_metadata_geometry(
                response['geometry']
            )
        return metadata
        

class RCM(Collection):
    def __init__(self, params):
        super().__init__(params)
        collection = 'RCMImageProducts'
        self.query_params = convert_params(params, collection)
        self.meta_keys = generate_meta_keys(collection)
        self.search_url = self.search_url.format(collection=collection, query='{query}', maxResults=self.maxResults)
    
    def construct_query(self):
        query = query_params.get('some_param', 'test text to go in >=')
        query = quote(query)
        self.search_url = self.search_url.format(query=query)

    def submit_order(self, order_ids):
        content = {
            'destinations': [],
            'items': [
                {
                    'collection': 'RCMImageProducts',
                    'recordId': recordId
                }
                for recordId in order_ids
            ]
        }
        r = self.session.post(self.order_url, data=content)


class RS2(Collection):
    def __init__(self, params):
        super().__init__(params)
        collection = 'Radarsat2'
        self.query_params = convert_params(params, collection)
        self.meta_keys = generate_meta_keys(collection)
        self.search_url = self.search_url.format(collection=collection, query='{query}', maxResults=self.maxResults)

    def construct_query(self, query_params):
        query = query_params.get('some_param', 'test text to go in >=')
        query = quote(query)
        self.search_url = self.search_url.format(query=query)
    

class RS1(Collection):
    def __init__(self, params):
        super().__init__(params)
        collection = 'Radarsat'
        self.query_params = convert_params(params, collection)
        self.meta_keys = generate_meta_keys(collection)        
        self.search_url = self.search_url.format(collection=collection, query='{query}', maxResults=self.maxResults)

    def construct_query(self, query_params):
        query = query_params.get('some_param', 'test text to go in >=')
        query = quote(query)
        self.search_url = self.search_url.format(query=query)
    

class NAPL(Collection):
    def __init__(self, params):
        super().__init__(params)
        collection = 'NAPL'
        self.query_params = convert_params(params, collection)
        self.meta_keys = generate_meta_keys(collection)        
        self.search_url = self.search_url.format(collection=collection, query='{query}', maxResults=self.maxResults)

    def construct_query(self, query_params):
        query = query_params.get('some_param', 'test text to go in >=')
        query = quote(query)
        self.search_url = self.search_url.format(query=query)


class Planet(Collection):
    def __init__(self, params):
        super().__init__(params)
        collection = 'PlanetScope'
        self.search_url = self.search_url.format(collection=collection, query='{query}')

    def construct_query(self, query_params):
        query = query_params.get('some_param', 'test text to go in >=')
        query = quote(query)
        self.search_url = self.search_url.format(query=query)
