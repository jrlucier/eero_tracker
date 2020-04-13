"""
Eero WiFi routers device_tracker for Home Assistant

For instructions and examples, see https://github.com/jrlucier/eero_tracker
"""
import logging
import voluptuous as vol
import datetime
import time
import re
import json
import requests
import homeassistant.helpers.config_validation as cv
from homeassistant.components.device_tracker.legacy import DeviceScanner
from homeassistant.components.device_tracker import PLATFORM_SCHEMA
from homeassistant.components.device_tracker.const import (
           DOMAIN, CONF_SCAN_INTERVAL, SCAN_INTERVAL)

_LOGGER = logging.getLogger(__name__)

CONF_ONLY_MACS_KEY = 'only_macs'
CONF_SESSION_FILE_NAME = 'session_file_name'
CONF_ONLY_NETWORKS = 'only_networks'

MINIMUM_SCAN_INTERVAL = 25

CACHE_EXPIRY=3600 # cache accounts for an hour

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_ONLY_MACS_KEY, default=''): cv.string,
    vol.Optional(CONF_ONLY_NETWORKS, default=[]): vol.All(cv.ensure_list, [cv.positive_int]),    
    vol.Optional(CONF_SESSION_FILE_NAME, default='eero.session'): cv.string
})

def get_scanner(hass, config):
    """Validate the configuration and return EeroDeviceScanner."""

    _LOGGER.debug(f"Initializing eero_tracker (domain {DOMAIN})")
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
        
        # configure any filters (macs or networks)
        self.__only_macs = set([x.strip().lower() for x in config[CONF_ONLY_MACS_KEY].split(',') if x != ''])
        if len(self.__only_macs) > 0:
            _LOGGER.info(f"Including only MAC addresses: {self.__only_macs}")

        self.__only_networks = set(config[CONF_ONLY_NETWORKS])
        if len(self.__only_networks) > 0:
            _LOGGER.info(f"Including only networks: {self.__only_networks}")

        self.__last_results = []
        self.__account = None
        self.__account_update_timestamp = None
        self.__mac_to_nickname = {}

        self.__scan_interval = config.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL) # datetime.timeinterval already

        # Prevent users from specifying an interval faster than 25 seconds
        minimum_interval = datetime.timedelta(seconds=MINIMUM_SCAN_INTERVAL)
        if self.__scan_interval < minimum_interval:
            _LOGGER.error(
                "Scan interval %d too frequent! Must be >= %d to prevent DDOSing eero's servers; limiting to %d seconds.",
                self.__scan_interval, MINIMUM_SCAN_INTERVAL, MINIMUM_SCAN_INTERVAL)
            self.__scan_interval = minimum_interval
        else:
            _LOGGER.debug(f"Scan interval = {self.__scan_interval} seconds")

        # Grab the session key from the file
        try:
            _LOGGER.debug(f"Loading eero session key from '{self.__session_file}'")
            with open(self.__session_file, 'r') as f:
                self.__session = f.read().replace('\n', '')
        except IOError:
            _LOGGER.error(f"Could not find the eero.session file '{self.__session_file}'")
            self.__session = None

    def scan_devices(self):
        """Required for the API, handles returning results"""
        # Return empty array if the session was never started.
        if self.__session is None:
            return []

        self._update_info()
        return self.__last_results

    def get_device_name(self, mac):
        """Required for the API. None to indicate we don't know the devices true name"""
        return self.__mac_to_nickname.get(mac)

    def _update_info(self):
        """Retrieve the latest information from Eero for returning to HA."""
        # Cache the accounts for an hour. These rarely change and this reduces the
        # lookup requests to only 1 every update. This cache is reset on Home Assistant
        # restarts, so in an emergency a user can always restart Home Assistant to force update.
        if self.__account_update_timestamp is None or (time.time() - self.__account_update_timestamp) >= CACHE_EXPIRY:
            _LOGGER.debug(f"Updating eero account information cache (expires every {CACHE_EXPIRY} seconds)")
            self.__account = self._account()
            self.__account_update_timestamp = time.time()

        self.__mac_to_nickname = {}
        self.__last_results = []
        for network in self.__account['networks']['data']:
            match = re.search('/networks/(\d+)', network['url'])
            network_id = int(match.group(1))
            
            # if specific networks should be filtered, skip any not in the filter
            if len(self.__only_networks) > 0 and network_id not in self.__only_networks:
                _LOGGER.debug(f"Ignoring network {network_id} devices not in only_networks: {self.__only_networks}")
                continue

            # load all devices for this network, but only track connected wireless devices
            devices = self._devices(network['url'])
            json_obj = json.loads(json.dumps(devices, indent=4))
            self._update_tracked_devices(json_obj)

        return

    def _update_tracked_devices(self, devices_json_obj):
        for device in devices_json_obj:
            if device['wireless'] and device['connected']:
                mac = device['mac']
                nickname = device['nickname']

                if len(self.__only_macs) > 0 and mac not in self.__only_macs:
                    continue

                _LOGGER.debug(f"Network {network_id} device found: nickname={nickname}; host={device['hostname']}; mac={mac}")

                # Create a mapping of macs to nicknames for lookup by device_name, if a nickname is assigned
                if nickname:
                    self.__mac_to_nickname[mac] = nickname

                # Append a result
                self.__last_results.append(mac)

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
                _LOGGER.error(f"Eero connection failure: {exception.error_message}")

    def _login_refresh(self):
        """Refresh the Eero session"""
        response = self._post_req('login/refresh', cookies=self._cookie_dict)
        new_session = response.get('user_token')
        if not new_session:
            _LOGGER.error(f"Failed updating eero session key! {response}")
            return

        _LOGGER.debug(f"Updating {self.__session_file} with new session key")
        try:
            # update in-memory session first, in case there is any failure in writing to the
            # session file, at least this tracker will continue working until next HA restart
            self.__session = new_session

            # TODO: ideally write to a temp file, and if successful, then move to overwrite
            # the existing session file
            with open(self.__session_file, 'w+') as f:
                f.write(new_session)
        except IOError:
            _LOGGER.error(f"Could not update eero session key in {self.__session_file}")

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
        response_code = data['meta']['code']
        if response_code not in [ 200, 201 ]:
            raise EeroException(response_code, data['meta'].get('error', ""))
        return data.get('data', "")

    def _post_req(self, action, **kwargs):
        """POST a request"""
        response = requests.post(self.API_ENDPOINT.format(action), **kwargs)
        return self._parse_response(response)

    def _get_req(self, action, **kwargs):
        """GET a request"""
        response = requests.get(self.API_ENDPOINT.format(action), **kwargs)
        return self._parse_response(response)
