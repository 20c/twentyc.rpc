"""
Unittests for twentyc.rpc.client
"""

import pytest
import json
import uuid

import twentyc.rpc.client as client

## PREP

INVALID_DATA_ERROR = {"name" : "value required"}

def obj(id, name=None):
    return {
        "_id" : id,
        "name" : (name or str(uuid.uuid4()))
    }

def objs(num):
    return [obj(i) for i in range(num)]

def response(num, status=200, meta={}, headers={}):
    return {
        "status" : status,
        "content" : json.dumps({
            "meta" : meta,
            "data" : objs(num)
        }),
        "headers" : headers
    }

testData = {
    "_throw" : json.dumps({
        "meta" : { 
            "error" : "TEST_ERROR"
        }
    }),
    "_load" : json.dumps({
        "meta" : {},
        "data" : objs(1)
    }),
    "GET": {
        "/api/obj" : response(10),
        "/api/obj/1" : response(1),
        "/api/obj/2" : response(0, status=404)
    },
    "POST": {
        "/api/obj_201" : response(0, status=201, headers={"Location":"/api/obj/1"}),
        "/api/obj_401" : response(0, status=401),
        "/api/obj_400" : response(0, status=400, meta=INVALID_DATA_ERROR)
    },
    "PUT": {
        "/api/obj_200/1" : response(1),
        "/api/obj_401/1" : response(0, status=401),
        "/api/obj_400/1" : response(0, status=400, meta=INVALID_DATA_ERROR)
    }
}

class DummyResponse(object):
    def __init__(self, status, content, headers={}):
        self.status = status
        self.content = content
        self.headers = headers

    @property
    def data(self):
        return json.loads(self.content)

    def read(self, *args, **kwargs):
        return self.content

    def getheader(self, name):
        return self.headers.get(name)


class DummyClient(client.RestClient):
    
    testData = testData

    def _request(self, url, method="GET", data=None, cxn=None):
        
        """
        Instead of requesting to a HTTP connection we retrieve pre-crafted
        responses from testData
        """

        print method, url

        self._response = DummyResponse(**(self.testData.get(method).get(url)))
        return self._response


## TESTS

def test_instantiate_default():

    client = DummyClient()
    
    assert client.host == None
    assert client.port == None
    assert client.path == "/api/"
    assert client.user == None
    assert client.password == None
    assert client.timeout == None
    assert client.validate_ssl == True
    assert client.verbose == False
    assert client.ssl == True

def test_instantiate_arguments():
    
    kwargs = {
        "host" : "localhost",
        "port" : 1234,
        "path" : "/other/",
        "user" : "user",
        "password" : "pass",
        "timeout" : 4000,
        "validate_ssl" : False,
        "verbose" : True,
        "ssl" : False
    }

    client = DummyClient(**kwargs)
    for k,v in kwargs.items():
        assert getattr(client, k) == v

def test__url():
    c = DummyClient();
    assert c._url("obj") == "/api/obj"
    assert c._url("obj", 123) == "/api/obj/123"
    assert c._url("obj", 123, limit=1) == "/api/obj/123?limit=1"
    assert c._url("obj", 123, limit=1, skip=2) == "/api/obj/123?skip=2&limit=1"
    assert c._url("obj", limit=1) == "/api/obj?limit=1"

def test__throw():
    response_404 = DummyResponse(404, testData.get("_throw"))
    response_401 = DummyResponse(401, testData.get("_throw"))
    response_400 = DummyResponse(400, testData.get("_throw"))
    response_500 = DummyResponse(500, "{}")

    c = DummyClient();

    with pytest.raises(client.NotFoundException) as exc:
        c._throw(response_404, response_404.data)

        assert exc.value.message == "404 TEST_ERROR"

    with pytest.raises(client.PermissionDeniedException) as exc:
        c._throw(response_401, response_401.data)

        assert exc.value.message == "401 TEST_ERROR"

    with pytest.raises(client.InvalidRequestException) as exc:
        c._throw(response_400, response_400.data)

        assert exc.value.message == "400 TEST_ERROR"

    with pytest.raises(LookupError) as exc:
        c._throw(response_404, response_404.data)

    with pytest.raises(IOError) as exc:
        c._throw(response_401, response_401.data)

    with pytest.raises(ValueError) as exc:
        c._throw(response_400, response_400.data)

    with pytest.raises(Exception) as exc:
        c._throw(response_500, response_500.data)

        assert exc.value.message == "500 Internal error: Unknown"

def test__load():
    
    response_200 = DummyResponse(200, testData.get("_load")) 
    response_404 = DummyResponse(404, testData.get("_throw"))

    c = DummyClient()

    data = c._load(response_200)
    assert type(data) == list
    assert len(data) == 1
    assert data[0] == response_200.data.get("data")[0]

    with pytest.raises(client.NotFoundException) as exc:
        c._load(response_404)

def test__mangle_data():

    before = {
        "pk" : 1,
        "_rev" : 123,
        "_id" : 1
    }

    after = { "id" : 1 }

    c = DummyClient()

    c._mangle_data(before)
    assert before == after
    

def test_get():
    
    c = DummyClient()
    data = c.get("obj", 1)
    assert data == c._response.data.get("data") 

    with pytest.raises(client.NotFoundException) as exc:
        c.get("obj", 2)

def test_all():

    c = DummyClient()
    data = c.all("obj")
    assert len(data) == 10
    assert data == c._response.data.get("data")
    
def test_create():

    c = DummyClient()

    expected = json.loads(testData.get("GET").get("/api/obj/1").get("content"))
    data = c.create("obj_201", expected.get("data")[0])
    assert data == expected.get("data")

    with pytest.raises(client.PermissionDeniedException) as exc:
        data = c.create("obj_401", expected.get("data")[0])
    
    with pytest.raises(client.InvalidRequestException) as exc:
        data = c.create("obj_400", expected.get("data")[0])
        assert exc.value.extra == INVALID_DATA_ERROR 


def test_update():

    c = DummyClient()

    expected = json.loads(testData.get("PUT").get("/api/obj_200/1").get("content"))

    data = c.update("obj_200", 1, **expected.get("data")[0])
    assert data == expected.get("data")


