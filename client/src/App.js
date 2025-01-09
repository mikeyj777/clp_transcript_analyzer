import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './components/Home';
import Clp_transcripts from './components/Clp_transcripts';
import PokerAnalysis from './components/PokerAnalysis';
import './App.css';
import './styles/global.css';

const App = () => {
  return (
    <Router>
      <div>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/clp" element={<Clp_transcripts />} />
          <Route path="/analysis" element={<PokerAnalysis />} />
        </Routes>
      </div>
    </Router>
  );
};

export default App;