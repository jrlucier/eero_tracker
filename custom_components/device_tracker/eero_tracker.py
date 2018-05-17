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
    def __init__(self, status, error_message):
        super(EeroException, self).__init__()
        self.status = status
        self.error_message = error_message
  

class EeroDeviceScanner(DeviceScanner):
    """This class queries a Eero-based router."""

    API_ENDPOINT = 'https://api-user.e2ro.com/2.2/{}'

    def __init__(self, hass, config):
        """Initialize the scanner."""
        self.__session_file = hass.config.path(config[CONF_SESSION_FILE_NAME])
        self.__session = None
        self.__only_macs = set([x.strip() for x in config[CONF_ONLY_MACS_KEY].split('.') if x != '']) 
        self.__scan_interval = config[CONF_SCAN_INTERVAL]
        self.__last_results = []

        if self.__scan_interval < datetime.timedelta(seconds=25):
            _LOGGER.error('Disabled. Scan interval is too fast!  Must be 25 or greater to prevent DDOSing Eeros servers.')
            return

        try:
            with open(self.__session_file, 'r') as f:
                self.__session = f.read().replace('\n', '')
        except IOError:
            _LOGGER.error('Could not find the Eero session file at: {}'.format(self.__session_file))
            self.__session = None


    def scan_devices(self):
        if self.__session == None:
          return []

        self._update_info()
        _LOGGER.debug('active_hosts %s', str(self.__last_results))
        return self.__last_results

    def get_device_name(self, mac):
        return None

    def _update_info(self):
        """Retrieve latest information from the router."""
        account = self._account()
        self.__last_results = []
        for network in account['networks']['data']:
          devices = self._devices(network['url'])

          json_obj = json.loads(json.dumps(devices, indent=4))
          for device in json_obj:
            if device['wireless'] and device['connected']:
              if len(self.__only_macs) > 0 and device['mac'] not in self.__only_macs:
                continue

              _LOGGER.debug("{}, {}, {}".format(device['nickname'], device['hostname'], device['mac']))
              self.__last_results.append(device['mac'])

        return

    @property
    def _cookie_dict(self):
        return dict(s=self.__session)

    def _login(self, identifier):
        # type(string) -> string
        params = dict(login=identifier)
        data = self._postReq('login', params=params)
        return data['user_token']

    def _refreshed(self, func):
        try:
            return func()
        except EeroException as exception:
            if (exception.status == 401
                    and exception.error_message == 'error.session.refresh'):
                self._login_refresh()
                return func()
            else:
                _LOGGER.error('Eero connection failure: %s; %s', data['meta']['code'], data['meta'].get('error', ""))

    def _login_refresh(self):
        response = self._postReq('login/refresh', cookies=self._cookie_dict)
        self.__session = response['user_token']
        with open(self.__session_file, 'w+') as f:
            f.write(self.__session)


    def _account(self):
        return self._refreshed(lambda: self._getReq('account', cookies=self._cookie_dict))

    def _id_from_url(self, id_or_url):
        match = re.search('^[0-9]+$', id_or_url)
        if match:
            return match.group(0)
        match = re.search(r'\/([0-9]+)$', id_or_url)
        if match:
            return match.group(1)

    def _devices(self, network_id):
        return self._refreshed(lambda: self._getReq('networks/{}/devices'.format(self._id_from_url(network_id)), cookies=self._cookie_dict))

    def _parse_response(self, response):
        data = json.loads(response.text)
        if data['meta']['code'] is not 200 and data['meta']['code'] is not 201:            
            raise EeroException(data['meta']['code'], data['meta'].get('error', ""))
        return data.get('data', "")

    def _postReq(self, action, **kwargs):
        response = requests.post(self.API_ENDPOINT.format(action), **kwargs)
        return self._parse_response(response)

    def _getReq(self, action, **kwargs):
        response = requests.get(self.API_ENDPOINT.format(action), **kwargs)
        return self._parse_response(response)


