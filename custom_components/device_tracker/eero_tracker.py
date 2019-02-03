"""
Support for Eero routers.

Place this eero_tracker.py file in: ~/.homeassistant/custom_components/device_tracker/

Given a session which can be located via the original eero.py file.  Here's an example configuration.yaml for this:
device_tracker:
  - platform: eero_tracker
    consider_home: 300
    interval_seconds: 60
    only_macs: "11:22:33:44:55:66, 22:22:22:22:22:22"

"""
import logging
import voluptuous as vol
import datetime
import time
import re
import json
import requests
import homeassistant.helpers.config_validation as cv
from homeassistant.components.device_tracker import (
    DOMAIN, PLATFORM_SCHEMA, CONF_SCAN_INTERVAL, DeviceScanner)

REQUIREMENTS = ['requests==2.13.0']

_LOGGER = logging.getLogger(__name__)

CONF_ONLY_MACS_KEY = 'only_macs'
CONF_SESSION_FILE_NAME = 'session_file_name'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_ONLY_MACS_KEY, default=''): cv.string,
    vol.Optional(CONF_SESSION_FILE_NAME, default='eero.session'): cv.string
})


def get_scanner(hass, config):
    """Validate the configuration and return EeroDeviceScanner."""

    _LOGGER.debug('Eero init')
    return EeroDeviceScanner(hass, config[DOMAIN])


class EeroException(Exception):
    """A propagating error for Eero"""

    def __init__(self, status, error_message):
        super(EeroException, self).__init__()
        self.status = status
        self.error_message = error_message


class EeroDeviceScanner(DeviceScanner):
    """This class queries a Eero-based router for present devices."""

    API_ENDPOINT = 'https://api-user.e2ro.com/2.2/{}'

    def __init__(self, hass, config):
        """Initialize the scanner."""
        self.__session_file = hass.config.path(config[CONF_SESSION_FILE_NAME])
        self.__session = None
        self.__only_macs = set([x.strip().lower() for x in config[CONF_ONLY_MACS_KEY].split(',') if x != ''])
        self.__scan_interval = config[CONF_SCAN_INTERVAL]
        self.__last_results = []
        self.__account = None
        self.__account_update_timestamp = None
        self.__mac_to_nickname = {}

        # Prevent users from specifying an interval faster than 25.  This will block the tracker
        # from returning results by bailing out early
        if self.__scan_interval < datetime.timedelta(seconds=25):
            _LOGGER.error(
                'Disabled. Scan interval is too fast!  Must be 25 or greater to prevent DDOSing Eeros servers.')
            return

        # Grab the session from the file
        try:
            with open(self.__session_file, 'r') as f:
                self.__session = f.read().replace('\n', '')
        except IOError:
            _LOGGER.error('Could not find the eero.session file at: {}'.format(self.__session_file))
            self.__session = None

    def scan_devices(self):
        """Required for the API, handles returning results"""
        # Return empty array if the session was never started...usually by too fast a speed specified.
        if self.__session is None:
            return []

        self._update_info()
        return self.__last_results

    def get_device_name(self, mac):
        """Required for the API. None to indicate we don't know the devices true name"""
        return self.__mac_to_nickname.get(mac)

    def _update_info(self):
        """Retrieve the latest information from Eero for returning to HA."""
        # Cache the accounts for an hour...these should rarely change and reduces the lookup requests
        # we use to only 1 every update.
        if self.__account is None or self.__account_update_timestamp is None or \
                        (time.time() - self.__account_update_timestamp) > 3600:
            _LOGGER.debug("Updating eero account information cache...")
            self.__account = self._account()
            self.__account_update_timestamp = time.time()

        self.__mac_to_nickname = {}
        self.__last_results = []
        for network in self.__account['networks']['data']:
            devices = self._devices(network['url'])

            json_obj = json.loads(json.dumps(devices, indent=4))
            for device in json_obj:
                if device['wireless'] and device['connected']:

                    if len(self.__only_macs) > 0 and device['mac'] not in self.__only_macs:
                        continue

                    _LOGGER.debug(
                        "Device found: {}, {}, {}".format(device['nickname'], device['hostname'], device['mac']))

                    # Create a mapping of macs to nicknames for lookup by device_name, if a nickname is assigned
                    if device['nickname']:
                        self.__mac_to_nickname[device['mac']] = device['nickname']

                    # Append a result
                    self.__last_results.append(device['mac'])

        return

    @property
    def _cookie_dict(self):
        """Creates a session cookie"""
        return dict(s=self.__session)

    def _refreshed(self, func):
        """Handles if we need to refresh the logged in session or not"""
        try:
            return func()
        except EeroException as exception:
            if exception.status == 401 and exception.error_message == 'error.session.refresh':
                self._login_refresh()
                return func()
            else:
                _LOGGER.error('Eero connection failure: {}'.format(exception.error_message))

    def _login_refresh(self):
        """Refresh the Eero session"""
        response = self._post_req('login/refresh', cookies=self._cookie_dict)
        self.__session = response['user_token']
        with open(self.__session_file, 'w+') as f:
            f.write(self.__session)

    def _account(self):
        return self._refreshed(lambda: self._get_req('account', cookies=self._cookie_dict))

    @staticmethod
    def _id_from_url(id_or_url):
        """Handles grabbing the Eero ID from the URL"""
        match = re.search('^[0-9]+$', id_or_url)
        if match:
            return match.group(0)
        match = re.search(r'\/([0-9]+)$', id_or_url)
        if match:
            return match.group(1)

    def _devices(self, network_id):
        """Gets the list of devices from Eero"""
        return self._refreshed(lambda: self._get_req('networks/{}/devices'.format(self._id_from_url(network_id)),
                                                     cookies=self._cookie_dict))

    @staticmethod
    def _parse_response(response):
        """Basic response handler"""
        data = json.loads(response.text)
        if data['meta']['code'] is not 200 and data['meta']['code'] is not 201:
            raise EeroException(data['meta']['code'], data['meta'].get('error', ""))
        return data.get('data', "")

    def _post_req(self, action, **kwargs):
        """POST a request"""
        response = requests.post(self.API_ENDPOINT.format(action), **kwargs)
        return self._parse_response(response)

    def _get_req(self, action, **kwargs):
        """GET a request"""
        response = requests.get(self.API_ENDPOINT.format(action), **kwargs)
        return self._parse_response(response)
