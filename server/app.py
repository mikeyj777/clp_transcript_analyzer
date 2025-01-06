# server\app.py
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import requests
from flask_cors import CORS

from utils.read_transcript_from_yt import scrape_transcript

import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


app = Flask(__name__)
CORS(app, resources={
    r"/*": {  # This specifically matches your API routes
        "origins": ["http://localhost:3000", "http://clp.riskspace.net"],
        "methods": ["GET", "POST", "OPTIONS"],  # Explicitly allow methods
        "allow_headers": ["Content-Type"]  # Allow common headers
    }
})


@app.route("/")
def home():
    return jsonify({"message": "This is the Emo Pop API."})

@app.route('/api/transcript', methods=['GET'])
def transcript_route():
    url = request.args.get('url')
    return scrape_transcript(url)

@app.route('/api/transcript-analysis', methods=['GET'])
def transcript_analysis_route():
    transcript = request.args.get('transcript')
    return 

if __name__ == '__main__':
    app.run("0.0.0.0", debug=True)