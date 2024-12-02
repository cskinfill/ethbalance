from flask import Flask, jsonify, abort
from prometheus_flask_exporter import PrometheusMetrics
import requests
import os
import uuid
import logging

app = Flask(__name__)
metrics = PrometheusMetrics(app)

metrics.info('app_info', 'Eth Balance', version='0.0.1')

logging.basicConfig(level=os.environ.get('LOG_LEVEL', 'INFO').upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_KEY = os.environ.get('API_KEY', default="TESTME")
HEADERS = {'Content-Type': 'application/json'}


def to_eths(weis):
    return weis * 1e-18


@app.route("/")
@metrics.do_not_track()
def hello_world():
    return jsonify([r.rule for r in app.url_map.iter_rules()])


@app.route("/address/balance/<address>")
def services(address, methods=["GET"]):
  request_id = uuid.uuid4().hex
  payload = {
    "jsonrpc": "2.0",
    "method": "eth_getBalance",
    "params": [
      address,
      "latest"
    ],
    "id": request_id
  }
  logger.debug(f"request payload is {payload}")
  r = requests.post(f"https://mainnet.infura.io/v3/{API_KEY}", headers=HEADERS, json=payload)
  logger.debug("Got back status code %s and body %s", r.status_code, r.text)
  if r.status_code == 200:
    resp = r.json()
    if "error" in resp:
      logger.warning(f"{resp["error"]}")
      abort(404)
    return jsonify({"balance": to_eths(int(resp["result"], base=16))})
  else:
    abort(404, "Not Found")

@app.route("/address/transaction/<address>")
def transaction(address, methods=["GET"]):
  request_id = uuid.uuid4().hex
  payload = {
    "jsonrpc": "2.0",
    "method": "eth_getTransactionByHash",
    "params": [
      address
    ],
    "id": request_id
  }
  logger.debug(f"request payload is {payload}")
  r = requests.post(f"https://mainnet.infura.io/v3/{API_KEY}", headers=HEADERS, json=payload)
  logger.debug("Got back status code %s and body %s", r.status_code, r.text)
  if r.status_code == 200:
    resp = r.json()
    if "error" in resp:
      logger.warning(f"{resp["error"]}")
      abort(404)
    return jsonify(resp["result"])
  else:
    abort(404, "Not Found")


if __name__ == "__main__":
    app.run(debug=True)
