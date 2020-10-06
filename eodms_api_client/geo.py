import geopandas as gpd
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, shape
from shapely.wkt import dumps

SRC_CRS = CRS('epsg:4326')

def transform_metadata_geometry(meta_geom, target_crs=None):
    '''
    EODMS always returns geometries in WGS84, so we provide the option to transform
    into something more useful through the use of a CLI flag (--t_srs)
    '''
    meta_geom = shape(meta_geom)
    if target_crs is None:
        return meta_geom
    elif isinstance(target_crs, CRS):
        dst_crs = target_crs
    else:
        dst_crs = CRS(target_crs)
    trans = Transformer.from_crs(
        crs_from=SRC_CRS,
        crs_to=dst_crs,
        always_xy=True
    )
    lons, lats = meta_geom.exterior.coords.xy
    xs, ys = trans.transform(xx=lons, yy=lats)
    return Polygon(zip(xs, ys))

def metadata_to_gdf(metadata, target_crs=None):
    if target_crs is None:
        crs = CRS('epsg:4326')
    elif isinstance(target_crs, CRS):
        crs = target_crs
    else:
        crs = CRS(target_crs)
    df = gpd.GeoDataFrame(metadata, crs=crs)
    df.rename(
        {
            'recordId': 'EODMS RecordId',
            'title': 'Granule'
        },
        axis=1,
        inplace=True
    )
    df.sort_values(by='EODMS RecordId', inplace=True)
    return df

def load_search_aoi(geofile):
    df = gpd.read_file(geofile)
    if df.crs != SRC_CRS:
        df = df.to_crs(SRC_CRS)
    geometry = df.unary_union
    if geometry.type == 'MultiPolygon':
        n_vertices = sum(
            [
                len(poly.exterior.coords) - 1
                for poly in geometry
            ]
        )
    elif geometry.type == 'Polygon':
        n_vertices = len(geometry.exterior.coords) - 1
    else:
        raise NotImplementedError('Search geometry must be a polygon/multipolygon')
    if n_vertices > 1000:
        raise Exception('Search geometry is too complex (more than 1000 vertices)')
    return dumps(geometry)
