import pytest
from app import app
import requests_mock

@pytest.fixture
def client():
    app.config['TESTING'] = True 
    with app.test_client() as client:
        yield client

def test_homepage(client):
    response = client.get('/')
    assert response.status_code == 200

def test_metrics(client):
    response = client.get('/metrics')
    assert response.status_code == 200

def test_balance(client):
    with requests_mock.Mocker() as m:
        m.post(f"https://mainnet.infura.io/v3/TESTME", json={"jsonrpc":"2.0","id":"583e4525a9514a498af430809c7dc02d","result":"0xaf4fe4c6730"})
        response = client.get('/address/balance/0xc94770007dda54cF92009BFF0dE90c06F603a09f')
        assert response.status_code == 200
        data = response.get_json()
        assert data["balance"] == 1.2047354718e-05

def test_balance_bad_address(client):
    with requests_mock.Mocker() as m:
        m.post(f"https://mainnet.infura.io/v3/TESTME", json={"jsonrpc":"2.0","id":1,"error":{"code":-32602,"message":"invalid argument 0: json: cannot unmarshal hex string of odd length into Go value of type common.Address"}})
        response = client.get('/address/balance/bob')
        assert response.status_code == 404