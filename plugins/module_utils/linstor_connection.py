# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os

HAS_LINSTOR = True
LINSTOR_IMPORT_ERROR = None

try:
    import linstor
except ImportError as e:
    HAS_LINSTOR = False
    LINSTOR_IMPORT_ERROR = str(e)


LINSTOR_COMMON_ARGS = dict(
    controllers=dict(
        type='str',
        default=None,
    ),
    auth_token=dict(
        type='str',
        default=None,
        no_log=True,
    ),
)


def linstor_argument_spec():
    """Base argument_spec dict shared by all LINSTOR modules."""
    return dict(LINSTOR_COMMON_ARGS)


def get_linstor_connection(module, unauthorized_ok=False):
    """Create and return a connected MultiLinstor instance.

    With unauthorized_ok=True an unauthorized connect (token
    authentication enabled but no usable token available) returns None
    instead of failing the module. Used by auth_init to detect an
    already initialized cluster without credentials.

    Controller URI resolution order (mirrors the linstor CLI):
    1. Module 'controllers' parameter (if provided)
    2. LS_CONTROLLERS environment variable
    3. ~/.config/linstor/linstor-client.conf (XDG user config)
    4. /etc/linstor/linstor-client.conf [global] controllers= key
    5. Fallback: linstor://localhost

    Steps 2-5 are handled by linstor.Config.get_controllers().
    SSL cert paths (certfile/keyfile/cafile) are read from the same
    config files in the same order, with user-level overriding system.

    Auth token resolution order (mirrors the linstor CLI):
    1. Module 'auth_token' parameter (if provided)
    2. linstor-client.conf [global] auth-token= key (user config
       overriding system config)
    3. /var/lib/linstor.d/auth.json fallback (handled inside
       python-linstor when no token is passed; satellite nodes only)
    """
    if not HAS_LINSTOR:
        module.fail_json(
            msg="python-linstor is required for this module. "
                "Install it with: pip install python-linstor. "
                "Import error: %s" % LINSTOR_IMPORT_ERROR)

    controllers_param = module.params.get('controllers')

    if controllers_param:
        uri_list = linstor.MultiLinstor.controller_uri_list(controllers_param)
    else:
        uri_list = linstor.Config.get_controllers()

    if not uri_list:
        uri_list = ['linstor://localhost']

    auth_token = module.params.get('auth_token')
    if not auth_token:
        auth_token = linstor.Config.get_section('global').get('auth-token')

    try:
        if auth_token:
            # The auth_token keyword requires a python-linstor release with
            # token authentication support; only pass it when a token is set
            # so older python-linstor keeps working without one.
            lin = linstor.MultiLinstor(uri_list, auth_token=auth_token)
        else:
            lin = linstor.MultiLinstor(uri_list)

        # Read SSL cert paths from linstor-client.conf for HTTPS/mTLS
        # System config first, then XDG user config; user-level wins.
        import configparser
        config = configparser.ConfigParser()
        xdg_config_home = os.environ.get(
            'XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        config.read([
            '/etc/linstor/linstor-client.conf',
            os.path.join(xdg_config_home, 'linstor', 'linstor-client.conf'),
        ])
        certfile = config.get('global', 'certfile', fallback=None)
        keyfile = config.get('global', 'keyfile', fallback=None)
        cafile = config.get('global', 'cafile', fallback=None)
        if certfile:
            lin.certfile = certfile
        if keyfile:
            lin.keyfile = keyfile
        if cafile:
            lin.cafile = cafile

        lin.connect()
    except linstor.LinstorError as e:
        if 'unauthorized' in str(e).lower():
            if unauthorized_ok:
                return None
            if not auth_token:
                module.fail_json(
                    msg="LINSTOR controller at %s requires token "
                        "authentication, but no token was found. Set the "
                        "auth_token parameter, add auth-token to "
                        "linstor-client.conf, or run the linbit.linstor.auth_init "
                        "role to initialize and save a token." % ', '.join(uri_list))
        module.fail_json(
            msg="Failed to connect to LINSTOR controller at %s: %s" % (
                ', '.join(uri_list), str(e)))

    return lin


def check_api_response(module, replies, action_description):
    """Check python-linstor API responses for errors.

    Calls module.fail_json with error details if any response indicates failure.
    """
    if not linstor.Linstor.all_api_responses_no_error(replies):
        errors = []
        for reply in replies:
            if hasattr(reply, 'ret_code'):
                if not linstor.Linstor.all_api_responses_no_error([reply]):
                    errors.append(str(reply))
            elif isinstance(reply, list):
                for item in reply:
                    if hasattr(item, 'ret_code') and not linstor.Linstor.all_api_responses_no_error([item]):
                        errors.append(str(item))
        module.fail_json(
            msg="LINSTOR API error during '%s': %s" % (
                action_description, '; '.join(errors) if errors else str(replies)))


def compute_property_diff(current_props, desired_props, delete_props=None):
    """Compare current and desired properties, return changes needed.

    Returns:
        tuple: (props_to_set, props_to_delete) where props_to_set is a dict
               of properties to create/update and props_to_delete is a list
               of property keys to remove.
    """
    props_to_set = {}
    props_to_delete = []

    if desired_props:
        for key, value in desired_props.items():
            current_value = current_props.get(key)
            if current_value is None or str(current_value) != str(value):
                props_to_set[key] = str(value)

    if delete_props:
        for key in delete_props:
            if key in current_props:
                props_to_delete.append(key)

    return props_to_set, props_to_delete


def parse_size(size_str):
    """Convert a human-readable size string to KiB.

    Accepts formats like '1G', '500M', '100K', '1T', '1024' (bytes).
    Uses linstor.SizeCalc when available.
    """
    if not HAS_LINSTOR:
        raise ValueError("python-linstor is required for size parsing")

    return linstor.SizeCalc.auto_convert(str(size_str), linstor.SizeCalc.UNIT_KiB)
