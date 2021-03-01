from datetime import datetime, timedelta
from urllib.parse import quote
from math import floor, ceil

from dateutil.parser import parse

from .geo import load_search_aoi


def validate_query_args(args, collection):
    '''
    Try to validate as many keyword arguments as possible for the given
    EODMS collection

    Inputs:
      - args: dictionary of keyword arguments provided by the user
      - collection: EODMS collection to validate arguments against

    Outputs:
      - query: a properly-escaped query string ready to be sent to
        EODMS API
    '''
    query_args = []
    # general params
    start = args.get('start', None)
    if start is not None: #TODO: Multi-select
        if start == 'TODAY-1':
            start = datetime.today() - timedelta(1)
        else:
            start = parse(start)
    else:
        start = datetime.today() - timedelta(1)
    query_args.append('CATALOG_IMAGE.START_DATETIME>=\'%s\'' % start.isoformat())
    end = args.get('end', None)
    if end is not None: #TODO: Multi-select
        if end == 'TODAY':
            end = datetime.today()
        else:
            end = parse(end)
    else:
        end = datetime.today()
    query_args.append('CATALOG_IMAGE.STOP_DATETIME<=\'%s\'' % (end + timedelta(days=1)).isoformat())
    geometry = args.get('geometry', None)
    if geometry is not None:
        query_args.append('CATALOG_IMAGE.THE_GEOM_4326 INTERSECTS %s' % load_search_aoi(geometry))
    product_type = args.get('product_type', None)
    if product_type is not None: #TODO: Multi-select
        query_args.append('ARCHIVE_IMAGE.PRODUCT_TYPE=%s' % product_type.upper())
    # RCM products
    if collection == 'RCMImageProducts':
        beam_mode = args.get('beam_mode', None)
        if beam_mode is not None: #TODO: Multi-select
            query_args.append('RCM.SBEAM=%s' % beam_mode)
        mnemonic = args.get('mnemonic', None)
        if mnemonic is not None: #TODO: Multi-select
            query_args.append('RCM.BEAM_MNEMONIC=%s' % mnemonic)
        product_format = args.get('product_format', None)
        if product_format is not None:
            query_args.append('PRODUCT_FORMAT.FORMAT_NAME_E=%s' % product_format)
        look_direction = args.get('look_direction', None)
        if look_direction is not None:
            query_args.append('RCM.ANTENNA_ORIENTATION=%s' % look_direction)
        polarization = args.get('polarization', None)
        if polarization is not None: #TODO: Multi-select
            query_args.append('RCM.POLARIZATION=%s' % polarization.upper())
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
            query_args.append('RCM.ORBIT_REL=%d' % int(relative_orbit))
        downlink_segment = args.get('downlink_segment', None)
        if downlink_segment is not None:
            query_args.append('RCM.DOWNLINK_SEGMENT_ID=%s' % downlink_segment)
    # Radarsat2 Products
    elif collection == 'Radarsat2':
        mnemonic = args.get('mnemonic', None)
        if mnemonic is not None: #TODO: Multi-select
            query_args.append('RSAT2.BEAM_MNEMONIC=%s' % mnemonic)
        look_direction = args.get('look_direction', None)
        if look_direction is not None:
            query_args.append('RSAT2.ANTENNA_ORIENTATION=%s' % look_direction)
        incidence_angle = args.get('incidence_angle', None)
        if incidence_angle is not None:
            query_args.append('RSAT2.INCIDENCE_ANGLE=%f' % float(incidence_angle))
        orbit_direction = args.get('orbit_direction', None)
        if orbit_direction is not None:
            query_args.append('RSAT2.ORBIT_DIRECTION=%s' % orbit_direction.capitalize())
        absolute_orbit = args.get('absolute_orbit', None)
        if absolute_orbit is not None: #TODO: Multi-select
            query_args.append('RSAT2.ORBIT_ABS=%f' % float(absolute_orbit))
        relative_orbit = args.get('relative_orbit', None)
        if relative_orbit is not None: #TODO: Multi-select
            query_args.append('RSAT2.ORBIT_REL=%d' % int(relative_orbit))
    # Radarsat1 Products
    elif collection == 'Radarsat1':
        mnemonic = args.get('mnemonic', None)
        if mnemonic is not None: #TODO: Multi-select
            query_args.append('RSAT1.BEAM_MNEMONIC=%s' % mnemonic)
        look_direction = args.get('look_direction', None)
        if look_direction is not None:
            query_args.append('RSAT1.ANTENNA_ORIENTATION=%s' % look_direction)
        incidence_angle = args.get('incidence_angle', None)
        if incidence_angle is not None:
            query_args.append('RSAT1.INCIDENCE_ANGLE=%f' % float(incidence_angle))
        orbit_direction = args.get('orbit_direction', None)
        if orbit_direction is not None:
            query_args.append('RSAT1.ORBIT_DIRECTION=%s' % orbit_direction.capitalize())
        absolute_orbit = args.get('absolute_orbit', None)
        if absolute_orbit is not None: #TODO: Multi-select
            query_args.append('RSAT1.ORBIT_ABS=%f' % float(absolute_orbit))
    # PlanetScope products
    elif collection == 'PlanetScope':
        cloud_cover = args.get('cloud_cover', None)
        if cloud_cover is not None:
            query_args.append('SATOPT.CLOUD_PERCENT=%d' % cloud_cover)
        incidence_angle_low = args.get('incidence_angle_low', None)
        if incidence_angle_low is not None:
            query_args.append('SENSOR_BEAM_CONFIG.INCIDENCE_LOW=%d' % floor(float(incidence_angle_low)))
        incidence_angle_high = args.get('incidence_angle_high', None)
        if incidence_angle_high is not None:
            query_args.append('SENSOR_BEAM_CONFIG.INCIDENCE_HIGH=%d' % ceil(float(incidence_angle_high)))            
    else:
        raise NotImplementedError(
            '%s is not implemented and/or not recognized as a valid EODMS collection'
            % collection
        )
    query = quote(' AND '.join(query_args))
    return query

def generate_meta_keys(collection):
    '''
    For the given collection, return the various keys that will be used to pull image metadata
    from EODMS
    '''
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
            'Sequence Id', 'Supplier Order Number', 'Start Date', 'End Date', 'Position', 'Sensor', 'Sensor Mode',
            'Beam', 'Polarization', 'Look Orientation', 'Incidence Angle (Low)',
            'Incidence Angle (High)', 'Orbit Direction', 'Absolute Orbit', 'LUT Applied',
            'Product Format', 'Product Type', 'Spatial Resolution',
        ]
    elif collection == 'Radarsat1':
        return [
            'Sequence Id', 'Product Id', 'Start Date', 'End Date', 'Position', 'Sensor', 'Sensor Mode',
            'Beam', 'Polarization', 'Look Orientation', 'Incidence Angle (Low)',
            'Incidence Angle (High)', 'Orbit Direction', 'Absolute Orbit', 'LUT Applied',
            'Product Format', 'Product Type', 'Spatial Resolution',
        ]
    elif collection == 'PlanetScope':
        return [
            'Sequence Id', 'Title', 'Start Date', 'End Date', 'Beam', 'Cloud Cover', 'Product Format',
            'Product Type', 'Sun Azimuth Angle', 'Sun Elevation Angle', 'SIP Size (MB)'
        ]
    else:
        raise NotImplementedError(
            '%s is not implemented and/or not recognized as a valid EODMS collection'
            % collection
        )
