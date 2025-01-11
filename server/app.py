# server\app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from utils.read_transcript_from_yt import get_transcript
from controllers.analysis_controller import hand_analysis
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    return jsonify({
        "message": "Poker Hand Analysis API",
        "version": "1.0",
        "status": "running"
    })

@app.route('/api/transcript', methods=['GET'])
def transcript_route():
    url = request.args.get('url')
    if not url:
        return jsonify({
            "status": "error",
            "message": "URL parameter is required"
        }), 400
    return get_transcript(url)

@app.route('/api/analyze', methods=['POST'])
def transcript_analysis_route():
    data = request.get_json()  # For POST request with JSON body
    query = data.get('query')
    logger.debug(f"Received query: {query}")
    if not query:
        return jsonify({
            "status": "error",
            "message": "userInput parameter is required"
        }), 400
        
    try:
        num_results = int(request.args.get('numResults', 5))
        if num_results < 1 or num_results > 20:  # Set reasonable limits
            num_results = 5
            logger.warning(f"Invalid numResults value, defaulting to 5")
    except (TypeError, ValueError):
        num_results = 5
        logger.warning(f"Invalid numResults format, defaulting to 5")

    try:
        resp = hand_analysis(query, num_results)
        return resp
    except Exception as e:
        logger.error(f"Error in hand analysis: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "An error occurred during analysis"
        }), 500

if __name__ == '__main__':
    app.run("0.0.0.0", debug=True)