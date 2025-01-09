import React, { useState } from 'react';

const PokerAnalysis = () => {
  const [userInput, setUserInput] = useState('');
  const [response, setResponse] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: userInput })
      });
      
      if (!response.ok) {
        throw new Error('Analysis failed');
      }
      
      const data = await response.json();
      setResponse(data.result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="poker-analysis-container">
      {/* Left side - Input visualization area */}
      <div className="input-section">
        <form onSubmit={handleSubmit}>
          <textarea
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            placeholder="Enter your poker hand or situation here..."
            className="input-textarea"
          />
        </form>
      </div>

      {/* Middle - Control section */}
      <div className="control-section">
        <button
          onClick={handleSubmit}
          disabled={loading || !userInput.trim()}
          className={`submit-button ${loading ? 'loading' : ''} ${!userInput.trim() ? 'disabled' : ''}`}
        >
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>

      {/* Right side - Parameters/results area */}
      <div className="results-section">
        {error && (
          <div className="error-alert">
            <p>{error}</p>
          </div>
        )}
        {response ? (
          <div className="results-content">
            <h3>Analysis Result</h3>
            <p>{response}</p>
          </div>
        ) : (
          <div className="results-placeholder">
            Analysis results will appear here
          </div>
        )}
      </div>
    </div>
  );
};

export default PokerAnalysis;