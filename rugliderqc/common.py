#!/usr/bin/env python

import os
import re
import pytz
from dateutil import parser
from netCDF4 import default_fillvals


def find_glider_deployment_datapath(logger, deployment, deployments_root, dataset_type, cdm_data_type, mode):
    glider_regex = re.compile(r'^(.*)-(\d{8}T\d{4})')
    match = glider_regex.search(deployment)
    if match:
        try:
            (glider, trajectory) = match.groups()
            try:
                trajectory_dt = parser.parse(trajectory).replace(tzinfo=pytz.UTC)
            except ValueError as e:
                logger.error('Error parsing trajectory date {:s}: {:}'.format(trajectory, e))
                trajectory_dt = None
                data_path = None
                deployment_location = None

            if trajectory_dt:
                trajectory = '{:s}-{:s}'.format(glider, trajectory_dt.strftime('%Y%m%dT%H%M'))
                deployment_name = os.path.join('{:0.0f}'.format(trajectory_dt.year), trajectory)

                # Create fully-qualified path to the deployment location
                deployment_location = os.path.join(deployments_root, deployment_name)
                if os.path.isdir(deployment_location):
                    # Set the deployment netcdf data path
                    data_path = os.path.join(deployment_location, 'data', 'out', 'nc',
                                             '{:s}-{:s}/{:s}'.format(dataset_type, cdm_data_type, mode))
                    if not os.path.isdir(data_path):
                        logger.warning('{:s} data directory not found: {:s}'.format(trajectory, data_path))
                        data_path = None
                        deployment_location = None
                else:
                    logger.warning('Deployment location does not exist: {:s}'.format(deployment_location))
                    data_path = None
                    deployment_location = None

        except ValueError as e:
            logger.error('Error parsing invalid deployment name {:s}: {:}'.format(deployment, e))
            data_path = None
            deployment_location = None
    else:
        logger.error('Cannot pull glider name from {:}'.format(deployment))
        data_path = None
        deployment_location = None

    return data_path, deployment_location


def find_glider_deployments_rootdir(logger, test):
    # Find the glider deployments root directory
    if test:
        envvar = 'GLIDER_DATA_HOME_TEST'
    else:
        envvar = 'GLIDER_DATA_HOME'

    data_home = os.getenv(envvar)

    if not data_home:
        logger.error('{:s} not set'.format(envvar))
        return 1, 1
    elif not os.path.isdir(data_home):
        logger.error('Invalid {:s}: {:s}'.format(envvar, data_home))
        return 1, 1

    deployments_root = os.path.join(data_home, 'deployments')
    if not os.path.isdir(deployments_root):
        logger.warning('Invalid deployments root: {:s}'.format(deployments_root))
        return 1, 1

    return data_home, deployments_root


def set_encoding(data_array, original_encoding=None):
    """
    Define encoding for a data array, using the original encoding from another variable (if applicable)
    :param data_array: data array to which encoding is added
    :param original_encoding: optional encoding dictionary from the parent variable
    (e.g. use the encoding from "depth" for the new depth_interpolated variable)
    """
    if original_encoding:
        data_array.encoding = original_encoding

    try:
        encoding_dtype = data_array.encoding['dtype']
    except KeyError:
        data_array.encoding['dtype'] = data_array.dtype

    try:
        encoding_fillvalue = data_array.encoding['_FillValue']
    except KeyError:
        # set the fill value using netCDF4.default_fillvals
        data_type = f'{data_array.dtype.kind}{data_array.dtype.itemsize}'
        data_array.encoding['_FillValue'] = default_fillvals[data_type]
