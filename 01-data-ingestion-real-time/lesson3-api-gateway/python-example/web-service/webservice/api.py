#!flask/bin/python
import os
import sys
from pathlib import Path

from flask import Flask, logging
from flask_cors import CORS

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from webservice.endpoint_data_ingestion import create_data_ingestion_without_fallback_storage
from webservice.endpoint_data_ingestion_fallback import create_data_ingestion_with_fallback_storage

app = Flask(__name__.split('.')[0])
CORS(app, allow_headers='*')

if __name__ == '__main__':
    os.makedirs('/tmp/bde-snippets-3/lesson3/fallback/', exist_ok=True)
    # Here we include the definitions for all endpoint
    create_data_ingestion_without_fallback_storage(app)
    create_data_ingestion_with_fallback_storage(app)

    app.run(debug=True, port=8080)
