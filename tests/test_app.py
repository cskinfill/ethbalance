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
        m.post("https://mainnet.infura.io/v3/TESTME", json={"jsonrpc": "2.0", "id": "583e4525a9514a498af430809c7dc02d", "result": "0xaf4fe4c6730"})
        response = client.get('/address/balance/0xc94770007dda54cF92009BFF0dE90c06F603a09f')
        assert response.status_code == 200
        data = response.get_json()
        assert data["balance"] == 1.2047354718e-05


def test_balance_bad_address(client):
    with requests_mock.Mocker() as m:
        m.post("https://mainnet.infura.io/v3/TESTME", json={"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "invalid argument 0: json: cannot unmarshal hex string of odd length into Go value of type common.Address"}})
        response = client.get('/address/balance/bob')
        assert response.status_code == 404


def test_transaction(client):
    with requests_mock.Mocker() as m:
        result = {"accessList": [], "blockHash": "0xe15344314be52104f8a26a203dda6cfccab083873ce6077622b640dee35d729b", "blockNumber": "0x14543f5", "chainId": "0x1", "from": "0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5", "gas": "0x327e7", "gasPrice": "0x6d4e75091", "hash": "0xd2e0104c7cefd42f54abd1e51a25bf94b0b874172532f2b26add8e674e155386", "input": "0x", "maxFeePerGas": "0x6d4e75091", "maxPriorityFeePerGas": "0x0", "nonce": "0x1a798e", "r": "0x3354af115413006d52cf0d53347821c8d30e74f3b7a6aeb68fe9f37b77b83a76", "s": "0xec42cdaa70c7e420087492c2351ec9961330635b7a2bbbe49f32bc04eceab66", "to": "0x22eec85ba6a5cd97ead4728ea1c69e1d9c6fa778", "transactionIndex": "0x112", "type": "0x2", "v": "0x0", "value": "0x10983111ba41c66", "yParity": "0x0"}
        m.post("https://mainnet.infura.io/v3/TESTME", json={"jsonrpc": "2.0", "id": "583e4525a9514a498af430809c7dc02d", "result": result})
        response = client.get('/address/transaction/0xc94770007dda54cF92009BFF0dE90c06F603a09f')
        assert response.status_code == 200
        data = response.get_json()
        assert data == result
