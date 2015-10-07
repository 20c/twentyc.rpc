#!/bin/env python

import base64
import httplib
import json
import urllib
import urlparse


class NotFoundException(LookupError):
    pass

class PermissionDeniedException(IOError):
    pass

class InvalidRequestException(ValueError):

    def __init__(self, msg, extra):
        Exception.__init__(self, msg)
        self.extra = extra

class RestClient(object):

    def __init__(self, **kwargs):
        """
        RESTful client


        """
        self.host = None
        self.port = None
        self.path = '/api/'
        self.user = None
        self.password = None
        self.timeout = None
        self.validate_ssl = True
        self.verbose = False
        self.ssl = kwargs.get("ssl", True)

        # overwrite any param from keyword args
        for k in kwargs:
            if hasattr(self, k):
                setattr(self, k, kwargs[k])

    def _url(self, __typ, __id=None, **kwargs):
        """
        Build URL for connection
        """
        url = self.path + __typ

        if __id:
            url += '/' + str(__id)

        if kwargs:
            url += '?' + urllib.urlencode(kwargs)

        return url

    def _request(self, url, method='GET', data=None, cxn=None):
        """
        send the request, return response obj
        """
        if not cxn:
            if self.ssl:
              cxn = httplib.HTTPSConnection(self.host, self.port, strict=True, timeout=self.timeout)
            else:
              cxn = httplib.HTTPConnection(self.host, self.port, strict=True, timeout=self.timeout)

        headers = {
                  "Accept": "application/json"
                  }

        if self.user:
            auth = 'Basic ' + base64.urlsafe_b64encode("%s:%s" % (self.user, self.password))
            headers['Authorization'] = auth

        if data:
            data = json.dumps(data)
            headers["Content-length"] = len(data)
            headers["Content-type"] = "application/json"

        self.log("%s %s headers:'%s' data:'%s' " % (method, url, str(headers), str(data)))
        cxn.request(method, url, data, headers)
        return cxn.getresponse()

    def _throw(self, res, data):
        self.log('=====> %s' %  data)
        err = data.get('meta', {}).get('error', 'Unknown')
        if res.status < 600:
            if res.status == 404:
                raise NotFoundException("%d %s" % (res.status, err))
            elif res.status == 401 or res.status == 403:
                raise PermissionDeniedException("%d %s" % (res.status, err))
            elif res.status == 400:
                raise InvalidRequestException("%d %s" % (res.status, err), data)

        # Internal
        raise Exception("%d Internal error: %s" % (res.status, err))

    def _load(self, res):
        try:
            data = json.load(res)

        except ValueError:
            data = {}

        if res.status < 300:
            if not data:
                return []
            return data.get('data', [])

        self._throw(res, data)

    def _mangle_data(self, data):
        if not 'id' in data and 'pk' in data:
            data['id'] = data['pk']
        if '_rev' in data:
            del data['_rev']
        if 'pk' in data:
            del data['pk']
        if '_id' in data:
            del data['_id']

    def log(self, msg):
        if self.verbose:
            print msg

    def all(self, typ, **kwargs):
        """
        List all of type
        Valid arguments:
            skip : number of records to skip
            limit : number of records to limit request to
        """
        return self._load(self._request(self._url(typ, **kwargs)))

    def get(self, typ, id):
        """
        Load type by id
        """
        return self._load(self._request(self._url(typ, id)))

    def create(self, typ, data, return_response=False):
        """
        Create new type
        Valid arguments:
            skip : number of records to skip
            limit : number of records to limit request to
        """
        res = self._request(self._url(typ), 'POST', data)
        if res.status != 201:
            data = res.read()
            try:
              self._throw(res, json.loads(data))
            except ValueError:
              self._throw(res, {})

        loc = res.getheader('Location')
        if loc and loc.startswith('/'):
            return self._load(self._request(loc))
        if return_response:
          return res.read()

        url = urlparse.urlparse(loc)
        if self.ssl:
          cxn = httplib.HTTPSConnection(url.netloc, strict=True, timeout=self.timeout, user=self.user, password=self.password)
        else:
          cxn = httplib.HTTPConnection(url.netloc, strict=True, timeout=self.timeout, user=self.user, password=self.password)
# TODO check scheme, add args
        return self._load(self._request(url.path, cxn=cxn))

    def update(self, typ, id, **kwargs):
        """
        update just fields sent by keyword args
        """
        return self._load(self._request(self._url(typ, id), 'PUT', kwargs))

    def save(self, typ, data):
        """
        Save the dataset pointed to by data (create or update)
        """
        if 'id' in data:
            return self._load(self._request(self._url(typ, data['id']), 'PUT', data))

        return self.create(typ, data)

    def rm(self, typ, id):
        """
        remove typ by id
        """
        return self._load(self._request(self._url(typ, id), 'DELETE'))


class TypeWrap(object):
    def __init__(self, client, typ):
        self.client = client
        self.typ = typ

    def all(self, **kwargs):
        """
        List all
        """
        return self.client.all(self.typ, **kwargs)

    def get(self, id):
        """
        Load by id
        """
        return self.client.get(self.typ, id)

    def save(self, data):
        """
        Save object
        """
        return self.client.save(self.typ, data)

    def rm(self, id):
        """
        remove by id
        """
        return self.client.rm(self.typ, id)

