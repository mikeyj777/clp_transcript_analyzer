import React, { useState } from 'react';
import { getYouTubeTranscript } from '../utils/helpers';
import '../styles/Clp_transcripts.css';

const ClpTranscripts = () => {
  const [url, setUrl] = useState('');
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await getYouTubeTranscript(url);
      setTranscript(result);
    } catch (err) {
      setError(err.message || 'Failed to fetch transcript');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="transcripts-container">
      <div className="transcript-content">
        {transcript ? (
          <div className="transcript-text">
            <h2>Video Transcript</h2>
            <pre>{transcript}</pre>
          </div>
        ) : (
          <div className="placeholder-text">
            Enter a YouTube URL to see its transcript
          </div>
        )}
      </div>
      
      <div className="controls-panel">
        <h1>YouTube Transcript Viewer</h1>
        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label htmlFor="youtube-url">YouTube URL</label>
            <input
              id="youtube-url"
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
            />
          </div>
          <button 
            type="submit" 
            disabled={loading || !url}
            className="submit-button"
          >
            {loading ? 'Loading...' : 'Get Transcript'}
          </button>
        </form>
        
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
      </div>
    </div>
  );
};

export default ClpTranscripts;