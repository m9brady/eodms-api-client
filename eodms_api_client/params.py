from datetime import datetime, timedelta
from math import ceil, floor
from urllib.parse import quote

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
    query_args.append("CATALOG_IMAGE.START_DATETIME>='%s'" % start.isoformat())
    end = args.get('end', None)
    if end is not None: #TODO: Multi-select
        if end == 'TODAY':
            end = datetime.today()
        else:
            end = parse(end)
    else:
        end = datetime.today()
    query_args.append("CATALOG_IMAGE.STOP_DATETIME<='%s'" % (end + timedelta(days=1)).isoformat())
    geometry = args.get('geometry', None)
    if geometry is not None:
        query_args.append('CATALOG_IMAGE.THE_GEOM_4326 INTERSECTS %s' % load_search_aoi(geometry))
    product_type = args.get('product_type', [None])
    if not isinstance(product_type, (list, tuple)): # single
        query_args.append("ARCHIVE_IMAGE.PRODUCT_TYPE='%s'" % product_type.upper())
    elif not (len(product_type) == 1 and product_type[0] is None): # multi
        query_args.append("ARCHIVE_IMAGE.PRODUCT_TYPE=%s" % ','.join([
            f'{prod_type.upper()!r}' for prod_type in product_type
        ]))
    # RCM products
    if collection == 'RCMImageProducts':
        beam_mode = args.get('beam_mode', [None])
        if not isinstance(beam_mode, (list, tuple)): # single
            query_args.append("RCM.SBEAM='%s'" % beam_mode)
        elif not (len(beam_mode) == 1 and beam_mode[0] is None): # multi
            query_args.append("RCM.SBEAM=%s" % ','.join(
                [f'{bm!r}' for bm in beam_mode]
            ))
        mnemonic = args.get('mnemonic', [None])
        if not isinstance(mnemonic, (list, tuple)): # single
             query_args.append("RCM.BEAM_MNEMONIC='%s'" % mnemonic)
        elif not (len(mnemonic) == 1 and mnemonic[0] is None): # multi
            query_args.append("RCM.BEAM_MNEMONIC=%s" % ','.join(
                [f'{m!r}' for m in mnemonic]
            ))
        product_format = args.get('product_format', None)
        if product_format is not None:
            query_args.append("PRODUCT_FORMAT.FORMAT_NAME_E='%s'" % product_format)
        look_direction = args.get('look_direction', None)
        if look_direction is not None:
            query_args.append("RCM.ANTENNA_ORIENTATION='%s'" % look_direction)
        polarization = args.get('polarization', [None])
        if not isinstance(polarization, (list, tuple)): # single
            query_args.append("RCM.POLARIZATION='%s'" % polarization.upper())
        elif not (len(polarization) == 1 and polarization[0] is None): # multi
            query_args.append("RCM.POLARIZATION=%s" % ','.join([
                f'{pol.upper()!r}' for pol in polarization
            ]))
        incidence_angle = args.get('incidence_angle', None)
        if incidence_angle is not None:
            query_args.append('RCM.INCIDENCE_ANGLE=%f' % float(incidence_angle))
        incidence_angle_low = args.get('incidence_angle_low', None)
        if incidence_angle_low is not None: #TODO: multi-select
            query_args.append('SENSOR_BEAM_CONFIG.INCIDENCE_LOW>=%.1f' % float(incidence_angle_low))
        incidence_angle_high = args.get('incidence_angle_high', None)
        if incidence_angle_high is not None: #TODO: multi-select
            query_args.append('SENSOR_BEAM_CONFIG.INCIDENCE_HIGH<=%.1f' % float(incidence_angle_high))
        orbit_direction = args.get('orbit_direction', None)
        if orbit_direction is not None:
            query_args.append("RCM.ORBIT_DIRECTION='%s'" % orbit_direction.capitalize())
        absolute_orbit = args.get('absolute_orbit', [None])
        if not isinstance(absolute_orbit, (list, tuple)): # single
            query_args.append('RCM.ORBIT_ABS=%.1f' % absolute_orbit)
        elif not (len(absolute_orbit) == 1 and absolute_orbit[0] is None): # multi
            query_args.append('RCM.ORBIT_ABS=%s' % ','.join([
                '%.1f' % orbit for orbit in absolute_orbit
            ]))
        relative_orbit = args.get('relative_orbit', [None])
        if not isinstance(relative_orbit, (list, tuple)): # single
            query_args.append('RCM.ORBIT_REL=%d' % relative_orbit)
        elif not (len(relative_orbit) == 1 and relative_orbit[0] is None): # multi
            query_args.append('RCM.ORBIT_REL=%s' % ','.join([
                '%d' % orbit for orbit in relative_orbit
            ]))
        downlink_segment = args.get('downlink_segment', None)
        if downlink_segment is not None:
            query_args.append("RCM.DOWNLINK_SEGMENT_ID='%s'" % downlink_segment)
    # Radarsat2 Products
    elif collection == 'Radarsat2':
        beam_mode = args.get('beam_mode', [None])
        if not isinstance(beam_mode, (list, tuple)): # single
            query_args.append("RSAT2.SBEAM='%s'" % beam_mode)
        elif not (len(beam_mode) == 1 and beam_mode[0] is None): # multi
            query_args.append("RSAT2.SBEAM=%s" % ','.join(
                [f'{bm!r}' for bm in beam_mode]
            ))
        mnemonic = args.get('mnemonic', [None])
        if not isinstance(mnemonic, (list, tuple)): # single
            query_args.append("RSAT2.BEAM_MNEMONIC='%s'" % mnemonic)
        elif not (len(mnemonic) == 1 and mnemonic[0] is None): # multi
            query_args.append("RSAT2.BEAM_MNEMONIC=%s" % ','.join(
                [f'{m!r}' for m in mnemonic]
            ))
        look_direction = args.get('look_direction', None)
        if look_direction is not None:
            query_args.append("RSAT2.ANTENNA_ORIENTATION='%s'" % look_direction)
        incidence_angle = args.get('incidence_angle', None)
        if incidence_angle is not None:
            query_args.append('RSAT2.INCIDENCE_ANGLE=%f' % float(incidence_angle))
        incidence_angle_low = args.get('incidence_angle_low', None)
        if incidence_angle_low is not None: #TODO: multi-select
            query_args.append('SENSOR_BEAM_CONFIG.INCIDENCE_LOW>=%.1f' % float(incidence_angle_low))
        incidence_angle_high = args.get('incidence_angle_high', None)
        if incidence_angle_high is not None: #TODO: multi-select
            query_args.append('SENSOR_BEAM_CONFIG.INCIDENCE_HIGH<=%.1f' % float(incidence_angle_high))            
        orbit_direction = args.get('orbit_direction', None)
        if orbit_direction is not None:
            query_args.append("RSAT2.ORBIT_DIRECTION='%s'" % orbit_direction.capitalize())
        absolute_orbit = args.get('absolute_orbit', [None])
        if not isinstance(absolute_orbit, (list, tuple)): # single
            query_args.append('RSAT2.ORBIT_ABS=%.1f' % absolute_orbit)
        elif not (len(absolute_orbit) == 1 and absolute_orbit[0] is None): # multi
            query_args.append('RSAT2.ORBIT_ABS=%s' % ','.join([
                '%.1f' % orbit for orbit in absolute_orbit
            ]))
        relative_orbit = args.get('relative_orbit', [None])
        if not isinstance(relative_orbit, (list, tuple)): # single
            query_args.append('RSAT2.ORBIT_REL=%d' % relative_orbit)
        elif not (len(relative_orbit) == 1 and relative_orbit[0] is None): # multi
            query_args.append('RSAT2.ORBIT_REL=%s' % ','.join([
                '%d' % orbit for orbit in relative_orbit
            ]))
    # Radarsat1 Products
    elif collection == 'Radarsat1':
        mnemonic = args.get('mnemonic', [None])
        if not isinstance(mnemonic, (list, tuple)): # single
            query_args.append("RSAT1.BEAM_MNEMONIC='%s'" % mnemonic)
        elif not (len(mnemonic) == 1 and mnemonic[0] is None): # multi
            query_args.append("RSAT1.BEAM_MNEMONIC=%s" % ','.join(
                [f'{m!r}' for m in mnemonic]
            ))
        look_direction = args.get('look_direction', None)
        if look_direction is not None:
            query_args.append("RSAT1.ANTENNA_ORIENTATION='%s'" % look_direction)
        incidence_angle = args.get('incidence_angle', None)
        if incidence_angle is not None:
            query_args.append('RSAT1.INCIDENCE_ANGLE=%f' % float(incidence_angle))
        incidence_angle_low = args.get('incidence_angle_low', None)
        if incidence_angle_low is not None: #TODO: multi-select
            query_args.append('SENSOR_BEAM_CONFIG.INCIDENCE_LOW>=%.1f' % float(incidence_angle_low))
        incidence_angle_high = args.get('incidence_angle_high', None)
        if incidence_angle_high is not None: #TODO: multi-select
            query_args.append('SENSOR_BEAM_CONFIG.INCIDENCE_HIGH<=%.1f' % float(incidence_angle_high))            
        orbit_direction = args.get('orbit_direction', None)
        if orbit_direction is not None:
            query_args.append("RSAT1.ORBIT_DIRECTION='%s'" % orbit_direction.capitalize())
        absolute_orbit = args.get('absolute_orbit', [None])
        if not isinstance(absolute_orbit, (list, tuple)): # single
            query_args.append('RSAT1.ORBIT_ABS=%.1f' % absolute_orbit)
        elif not (len(absolute_orbit) == 1 and absolute_orbit[0] is None): # multi
            query_args.append('RSAT1.ORBIT_ABS=%s' % ','.join([
                '%.1f' % orbit for orbit in absolute_orbit
            ]))
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
    # National Air Photo Library products
    elif collection == 'NAPL':
        roll_num = args.get('roll_number', None)
        #TODO: if roll_num or photo_num is given, remove the temporal search filter as only 1 result will be found
        if roll_num is not None:
            query_args.append('ROLL.ROLL_NUMBER=%s' % roll_num)
        photo_num = args.get('photo_number', None)
        if photo_num is not None:
            query_args.append('PHOTO.PHOTO_NUMBER=%s' % photo_num)
        napl_nocost = args.get('napl_nocost', None)
        if napl_nocost is not None:
            is_free = 't' if napl_nocost else 'f'
            query_args.append('CATALOG_IMAGE.OPEN_DATA=%f' % is_free)
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
            'Sampled Pixel Spacing', 'Data Type', 'SIP Size (MB)', 'Relative Orbit', 'Absolute Orbit',
            'Orbit Data Source'
        ]
    elif collection == 'Radarsat2':
        return [
            'Sequence Id', 'Supplier Order Number', 'Start Date', 'End Date', 'Position', 'Sensor', 'Sensor Mode',
            'Beam', 'Polarization', 'Look Orientation', 'Incidence Angle (Low)',
            'Incidence Angle (High)', 'Orbit Direction', 'Absolute Orbit', 'LUT Applied',
            'Product Format', 'Product Type', 'Spatial Resolution', 'SIP Size (MB)'
        ]
    elif collection == 'Radarsat1':
        return [
            'Sequence Id', 'Product Id', 'Start Date', 'End Date', 'Position', 'Sensor', 'Sensor Mode',
            'Beam', 'Polarization', 'Look Orientation', 'Incidence Angle (Low)',
            'Incidence Angle (High)', 'Orbit Direction', 'Absolute Orbit', 'LUT Applied',
            'Product Format', 'Product Type', 'Spatial Resolution', 'SIP Size (MB)'
        ]
    elif collection == 'PlanetScope':
        return [
            'Sequence Id', 'Title', 'Start Date', 'End Date', 'Beam', 'Cloud Cover', 'Product Format',
            'Product Type', 'Sun Azimuth Angle', 'Sun Elevation Angle', 'SIP Size (MB)'
        ]
    elif collection == 'NAPL':
        return [
            'Sequence Id', 'Title', 'Start Date', 'End Date', 'Altitude', 'Viewing Angle', 'Scale', 
            'SIP Size (MB)',
        ]
    else:
        raise NotImplementedError(
            '%s is not implemented and/or not recognized as a valid EODMS collection'
            % collection
        )

def available_query_args(collection):
    '''
    For a given EODMS collection, produce a dictionary of available query parameters for use in EodmsAPI.query calls
    '''
    # general params
    params = {
        'start': {'description': 'start time (UTC) of query temporal window', 'type': str},
        'end': {'description': 'end time (UTC) of query temporal window', 'type': str},
        'geometry': {'description': 'path to vector geometry file', 'type': str},
        'product_type': {'description': 'product type (e.g. "SLC", "GRD")', 'type': str}
    }
    # RCM products
    if collection == 'RCMImageProducts':
        params.update({
            'beam_mode': {'description': 'SAR beam mode (e.g. "Low Resolution 100m")', 'type': str},
            'mnemonic': {'description': 'SAR beam mode mnemonic (e.g. "SC100MA")', 'type': str},
            'product_format': {'description': 'Data format (e.g. "GeoTIFF"', 'type': str},
            'look_direction': {'description': 'Antenna look-direction (e.g. "Left", "Right")', 'type': str},
            'polarization': {'description': 'SAR beam polarization (e.g. "HH", "HH/HV")', 'type': str},
            'incidence_angle': {'description': 'Exact SAR incidence angle', 'type': float},
            'incidence_angle_low': {'description': 'Lower bound for SAR incidence angle', 'type': float},
            'incidence_angle_high': {'description': 'Upper bound for SAR incidence angle', 'type': float},
            'orbit_direction': {'description': 'Type of orbit (e.g. "Ascending", "Descending"', 'type': str},
            'absolute_orbit': {'description': 'Specific Orbit ID number', 'type': int},
            'relative_orbit': {'description': 'Relative Orbit ID number', 'type': int},
            'downlink_segment': {'description': 'Specific RCM downlink segment', 'type': str}
        })

    # Radarsat2 Products
    elif collection == 'Radarsat2':
        params.update({
            'beam_mode': {'description': 'SAR beam mode (e.g. "ScanSAR Wide")', 'type': str},
            'mnemonic': {'description': 'SAR beam mode mnemonic (e.g. "SCWA")', 'type': str},
            'product_format': {'description': 'Data format (e.g. "GeoTIFF"', 'type': str},
            'incidence_angle': {'description': 'Exact SAR incidence angle', 'type': float},
            'incidence_angle_low': {'description': 'Lower bound for SAR incidence angle', 'type': float},
            'incidence_angle_high': {'description': 'Upper bound for SAR incidence angle', 'type': float},
            'orbit_direction': {'description': 'Type of orbit (e.g. "Ascending", "Descending"', 'type': str},
            'absolute_orbit': {'description': 'Specific Orbit ID number', 'type': int},
            'relative_orbit': {'description': 'Relative Orbit ID number', 'type': int},
        })
    # Radarsat1 Products
    elif collection == 'Radarsat1':
        params.update({
            'mnemonic': {'description': 'SAR beam mode mnemonic (e.g. "SCWA")', 'type': str},
            'look_direction': {'description': 'Antenna look-direction (e.g. "Left", "Right")', 'type': str},
            'incidence_angle': {'description': 'Exact SAR incidence angle', 'type': float},
            'incidence_angle_low': {'description': 'Lower bound for SAR incidence angle', 'type': float},
            'incidence_angle_high': {'description': 'Upper bound for SAR incidence angle', 'type': float},
            'orbit_direction': {'description': 'Type of orbit (e.g. "Ascending", "Descending"', 'type': str},
            'absolute_orbit': {'description': 'Specific Orbit ID number', 'type': int},
        })
    # PlanetScope products
    elif collection == 'PlanetScope':
        params.update({
            'cloud_cover': {'description': 'Maximum allowable percent cloud cover', 'type': float},
            'incidence_angle_low': {'description': 'Lower bound for SAR incidence angle', 'type': float},
            'incidence_angle_high': {'description': 'Upper bound for SAR incidence angle', 'type': float},
        })
    # National Air Photo Library products
    elif collection == 'NAPL':
        params.update({
            'roll_number': {'description': 'AirpPhoto Roll Number (e.g. "A28523")', 'type': str},
            'photo_number': {'description': 'AirPhoto Number (e.g. "0016", "%%16")', 'type': str},
            #'napl_nocost': {'description': 'Whether or not to query for no-cost airphotos': 'type': bool}
        })
    else:
        raise NotImplementedError(
            '%s is not implemented and/or not recognized as a valid EODMS collection'
            % collection
        )
    return params
