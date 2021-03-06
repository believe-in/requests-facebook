__all__ = ('FacebookAPI', 'GraphAPI', 'FacebookClientError', \
            'FacebookAuthError', 'FacebookAPIError', 'GraphAPIError')

""" Requests-Facebook """

__author__ = 'Mike Helmick <mikehelmick@me.com>'
__version__ = '0.2.0'

from urllib import urlencode

try:
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl

try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
        try:
            from django.utils import simplejson as json
        except ImportError:
            raise ImportError('A json library is required to use this python library. Lol, yay for being verbose. ;)')

import requests


def _split_params_and_files(params_):
        params = {}
        files = {}
        for k, v in params_.items():
            if hasattr(v, 'read') and callable(v.read):
                files[k] = v
            elif isinstance(v, basestring):
                params[k] = v
            else:
                continue
        return params, files


class FacebookClientError(Exception):
    def __init__(self, message, error_type=None, error_code=None,
                 error_subcode=None):
        self.type = error_type

        self.message = message
        if error_type is not None:
            self.message = '%s: %s' % (error_type, message)

        super(FacebookClientError, self).__init__(self.message)


class FacebookAuthError(FacebookClientError):
    pass


class FacebookAPIError(FacebookClientError):
    pass


class GraphAPIError(FacebookClientError):

    def __init__(self, message, error_code=None, error_subcode=None,
                 error_type=None):

        self.error_code = error_code
        self.error_subcode = error_subcode
        super(GraphAPIError, self).__init__(message, error_code=error_code,
                                            error_subcode=error_subcode,
                                            error_type=error_type)


class FacebookAPI(object):
    def __init__(self, client_id=None, client_secret=None, redirect_uri=None,
                 headers=None):

        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

        # If there's headers, set them. If not, lets
        self.headers = headers or {'User-agent': 'Requests-Facebook %s' % __version__}

    def get_auth_url(self, display='popup', scope=None):
        scope = scope or []
        url = 'https://www.facebook.com/dialog/oauth'
        qs = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'display': display,
            'scope': ','.join(scope)
        }
        return '%s?%s' % (url, urlencode(qs))

    def get_access_token(self, code):
        url = 'https://graph.facebook.com/oauth/access_token'
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'code': code
        }

        return self.make_request(url, params)

    def exchange_access_token(self, code):
        url = 'https://graph.facebook.com/oauth/access_token'
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'fb_exchange_token': code
        }

        return self.make_request(url, params)

    def make_request(self, url, params):

        try:
            response = requests.get(url, params=params, headers=self.headers)
        except requests.OAuthException:
            raise FacebookAuthError('Invalid access token')

        status_code = response.status_code
        content = response.content

        if status_code != 200:
            try:
                content = json.loads(content)
            except ValueError:
                raise FacebookClientError('Unable to parse response, invalid JSON.')

            if content.get('error') is not None:
                error = content['error']
                error_type = error.get('type', '')
                error_message = error.get('message', '')

                raise FacebookAuthError(error_message, error_type=error_type)
            else:
                raise FacebookClientError('An unknown error occurred.')

        try:
            data = dict(parse_qsl(content))
        except AttributeError:
            raise FacebookAuthError('Unable to obtain access token.')

        return data

    def __repr__(self):
        return u'<FacebookAPI: %s>' % self.client_id


class GraphAPI(object):
    def __init__(self, access_token=None, headers=None):
        self.api_url = 'https://graph.facebook.com/'
        self.access_token = access_token

        # If there's headers, set them. If not, lets
        self.headers = headers or {'User-agent': 'Requests-Facebook %s' % __version__}

    def get(self, endpoint, params=None):
        return self.request(endpoint, params=params)

    def post(self, endpoint, params=None, files=None):
        return self.request(endpoint, method='POST', params=params)

    def delete(self, endpoint, params=None):
        return self.request(endpoint, method='DELETE', params=params)

    def request(self, endpoint, method='GET', params=None):
        params = params or {}

        url = self.api_url + endpoint + '?access_token=' + self.access_token
        method = method.lower()

        if not method in ('get', 'post', 'delete'):
            raise FacebookClientError('Method must be of GET, POST or DELETE')

        params, files = _split_params_and_files(params)

        func = getattr(requests, method)
        try:
            if method == 'get':
                response = func(url, params=params, headers=self.headers)
            else:
                response = func(url,
                                data=params,
                                files=files,
                                headers=self.headers)

        except requests.exceptions.RequestException:
            raise FacebookClientError('An unknown error occurred.')

        try:
            content = json.loads(response.content)
        except ValueError:
            raise FacebookClientError('Unable to parse response, invalid JSON.')

        if response.status_code != 200:
            if content.get('error') is not None:
                error = content['error']
                error_type = error.get('type', '')
                error_code = error.get('code', '')
                error_subcode = error.get('subcode', '')
                error_message = error.get('message', '')

                raise GraphAPIError(error_message,
                                    error_type=error_type,
                                    error_code=error_code,
                                    error_subcode=error_subcode)

        return content

    def __repr__(self):
        return u'<GraphAPI: %s>' % self.access_token
