from datetime import datetime, timedelta
from urllib.parse import quote

from dateutil.parser import parse

from .geo import load_search_aoi


def validate_query_args(args, collection):
    query_args = []
    # RCM products
    if collection == 'RCMImageProducts':
        start = args.get('start', None)
        if start is not None: #TODO: Multi-select
            if start == 'TODAY-1':
                start = datetime.today() - timedelta(1)
            else:
                start = parse(start)
            query_args.append('CATALOG_IMAGE.START_DATETIME>=\'%s\'' % start.isoformat())
        end = args.get('end', None)
        if end is not None: #TODO: Multi-select
            if end == 'TODAY':
                end = datetime.today()
            else:
                end = parse(end)
            query_args.append('CATALOG_IMAGE.START_DATETIME<\'%s\'' % end.isoformat())
        beam_mode = args.get('beam_mode', None)
        if beam_mode is not None: #TODO: Multi-select
            query_args.append('RCM.SBEAM=%s' % beam_mode)
        mnemonic = args.get('mnemonic', None)
        if mnemonic is not None: #TODO: Multi-select
            query_args.append('RCM.BEAM_MNEMONIC=%s' % mnemonic)
        product_type = args.get('product_type', None)
        if product_type is not None: #TODO: Multi-select
            query_args.append('ARCHIVE_IMAGE.PRODUCT_TYPE=%s' % product_type)
        polarization = args.get('polarization', None)
        if polarization is not None: #TODO: Multi-select
            query_args.append('RCM.POLARIZATION=%s' % polarization)
        incidence_angle = args.get('incidence_angle', None)
        if incidence_angle is not None:
            query_args.append('RCM.INCIDENCE_ANGLE=%f' % float(incidence_angle))
        orbit_direction = args.get('orbit_direction', None)
        if orbit_direction is not None:
            query_args.append('RCM.ORBIT_DIRECTION=%s' % orbit_direction.capitalize())
        absolute_orbit = args.get('absolute_orbit', None)
        if absolute_orbit is not None: #TODO: Multi-select
            query_args.append('RCM.ORBIT_ABS=%f' % float(absolute_orbit))
        relative_orbit = args.get('relative_orbit', None)
        if relative_orbit is not None: #TODO: Multi-select
            query_args.append('RCM.ORBIT_REL=%f' % int(relative_orbit))
        downlink_segment = args.get('downlink_segment', None)
        if downlink_segment is not None:
            query_args.append('RCM.DOWNLINK_SEGMENT_ID=%s' % downlink_segment)
    else:
        raise NotImplementedError('Only RCM is implemented right now')
    geometry = args.get('geometry', None)
    if geometry is not None:
        query_args.append('CATALOG_IMAGE.THE_GEOM_4326 INTERSECTS %s' % load_search_aoi(geometry))
    query = ' AND '.join(query_args)
    return quote(query)

def generate_meta_keys(collection):
    if collection == 'RCMImageProducts':
        return [
            'recordId', 'title', 'Acquisition Start Date', 'Acquisition End Date', 'Satellite ID',
            'Beam Mnemonic', 'Beam Mode Type', 'Beam Mode Description', 'Beam Mode Version',
            'Spatial Resolution', 'Polarization Data Mode', 'Polarization',
            'Polarization in Product', 'Number of Azimuth Looks', 'Number of Range Looks',
            'Incidence Angle (Low)', 'Incidence Angle (High)', 'Orbit Direction', 'LUT Applied',
            'Product Format', 'Product Type', 'Product Ellipsoid', 'Sample Type',
            'Sampled Pixel Spacing', 'Data Type', 'Relative Orbit', 'Absolute Orbit',
            'Orbit Data Source'
        ]
    elif collection == 'Radarsat2':
        return [

        ]
    elif collection == 'Radarsat':
        return [

        ]
    elif collection == 'NAPL':
        return [

        ]
    elif collection == 'PlanetScope':
        return [

        ]
    else:
        raise NotImplementedError(
            '%s collection is not implemented and/or not recognized as a valid EODMS collection'
            % collection
        )
