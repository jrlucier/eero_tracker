import re
import json
import requests
from argparse import ArgumentParser
from abc import abstractproperty

__version__ = "0.0.1"
__all__ = ['ClientException', 'Eero', 'SessionStorage', '__version__']


class Eero(object):
    def __init__(self, arg_session):
        # type(SessionStorage) -> ()
        self.session = arg_session
        self.client = Client()

    @property
    def _cookie_dict(self):
        if self.needs_login():
            return dict()
        else:
            return dict(s=self.session.cookie)

    def needs_login(self):
        return self.session.cookie is None

    def login(self, identifier):
        # type(string) -> string
        json = dict(login=identifier)
        data = self.client.post('login', json=json)
        return data['user_token']

    def login_verify(self, verification_code, user_token):
        json = dict(code=verification_code)
        response = self.client.post('login/verify', json=json,
                                    cookies=dict(s=user_token))
        self.session.cookie = user_token
        return response

    def refreshed(self, func):
        try:
            return func()
        except ClientException as exception:
            if exception.status == 401 and exception.error_message == 'error.session.refresh':
                self.login_refresh()
                return func()
            else:
                raise

    def login_refresh(self):
        response = self.client.post('login/refresh', cookies=self._cookie_dict)
        self.session.cookie = response['user_token']

    def account(self):
        return self.refreshed(lambda: self.client.get(
            'account',
            cookies=self._cookie_dict))

    @staticmethod
    def id_from_url(id_or_url):
        match = re.search('^[0-9]+$', id_or_url)
        if match:
            return match.group(0)
        match = re.search(r'\/([0-9]+)$', id_or_url)
        if match:
            return match.group(1)

    def devices(self, network_id):
        return self.refreshed(lambda: self.client.get(
            'networks/{}/devices'.format(
                self.id_from_url(network_id)), cookies=self._cookie_dict))


class SessionStorage(object):
    @abstractproperty
    def cookie(self):
        pass


class ClientException(Exception):
    def __init__(self, status, error_message):
        super(ClientException, self).__init__()
        self.status = status
        self.error_message = error_message


class Client(object):
    API_ENDPOINT = 'https://api-user.e2ro.com/2.2/{}'

    @staticmethod
    def _parse_response(response):
        data = json.loads(response.text)
        if data['meta']['code'] is not 200 and data['meta']['code'] is not 201:
            raise ClientException(data['meta']['code'],
                                  data['meta'].get('error', ""))
        return data.get('data', "")

    def post(self, action, **kwargs):
        response = requests.post(self.API_ENDPOINT.format(action), **kwargs)
        return self._parse_response(response)

    def get(self, action, **kwargs):
        response = requests.get(self.API_ENDPOINT.format(action), **kwargs)
        return self._parse_response(response)


class CookieStore(SessionStorage):
    def __init__(self, cookie_file):
        from os import path
        self.cookie_file = path.abspath(cookie_file)

        try:
            with open(self.cookie_file, 'r') as f:
                self.__cookie = f.read()
        except IOError:
            self.__cookie = None

    @property
    def cookie(self):
        return self.__cookie

    @cookie.setter
    def cookie(self, cookie):
        self.__cookie = cookie
        with open(self.cookie_file, 'w+') as f:
            f.write(self.__cookie)


session = CookieStore('eero.session')
eero = Eero(session)

if __name__ == '__main__':
    if eero.needs_login():

        try:
            input = raw_input
        except NameError:
            pass

        parser = ArgumentParser()
        parser.add_argument("-l", help="Your eero login (email address or SMS phone number)")
        args = parser.parse_args()
        if args.l:
            phone_number = args.l
        else:
            phone_number = input('Your eero login (email address or SMS phone number): ')
        user_token = eero.login(phone_number)
        verification_code = input('Verification key from email or SMS: ')
        eero.login_verify(verification_code, user_token)
        print('Login successful. eero.session created, you can now use the device_tracker.')
    else:
        print('eero.session already created dumping all devices')
        account = eero.account()
        for network in account['networks']['data']:
            devices = eero.devices(network['url'])

            json_obj = json.loads(json.dumps(devices, indent=4))
            for device in json_obj:
                if device['wireless'] and device['connected']:
                    print("{}, {}, {}".format(device['nickname'], device['hostname'], device['mac']))
