from urllib.parse import quote

def validate_query_args(args, collection):
    return quote('CREATE DATE >= 1')


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
