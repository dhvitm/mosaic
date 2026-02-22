import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Banknote, TrendingUp, FileSpreadsheet, Sparkles, Database, Settings } from "lucide-react";
import axios from "axios";
import JobsList from "../components/JobsList";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Landing() {
  const [ticker, setTicker] = useState("");
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [error, setError] = useState("");
  const [isValid, setIsValid] = useState(null);
  const navigate = useNavigate();

  // Debounced ticker validation
  useEffect(() => {
    const validateTicker = async () => {
      if (!ticker || ticker.length < 2) {
        setIsValid(null);
        return;
      }

      setValidating(true);
      try {
        const response = await axios.get(`${API}/generate/validate-ticker/${ticker}`);
        setIsValid(response.data.valid);
        if (!response.data.valid) {
          setError("Ticker not found on Screener.in");
        } else {
          setError("");
        }
      } catch (err) {
        // If validation fails, allow proceeding
        setIsValid(true);
        setError("");
      } finally {
        setValidating(false);
      }
    };

    const timeoutId = setTimeout(validateTicker, 800);
    return () => clearTimeout(timeoutId);
  }, [ticker]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    
    if (!ticker.trim()) {
      setError("Please enter a ticker");
      return;
    }

    if (isValid === false) {
      setError("Please enter a valid ticker");
      return;
    }

    setLoading(true);
    
    try {
      const response = await axios.post(`${API}/generate/`, {
        ticker: ticker.toUpperCase()
      });
      
      const jobId = response.data.id;
      navigate(`/processing/${jobId}`);
      
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create model job");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 relative overflow-hidden">
      {/* Animated Background Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.03)_1px,transparent_1px)] bg-[size:50px_50px] animate-[grid_20s_linear_infinite]"></div>
      
      {/* Radial Gradient */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-gradient-radial from-indigo-500/20 via-transparent to-transparent blur-3xl"></div>
      
      {/* Hero Background Image */}
      <div 
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: 'url(https://images.pexels.com/photos/16553906/pexels-photo-16553906.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          filter: 'brightness(0.3)'
        }}
      ></div>

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4">
        
        {/* Navigation */}
        <div className="absolute top-8 right-8 flex items-center gap-3">
          <Link
            to="/admin"
            className="px-4 py-2 bg-slate-800/50 hover:bg-slate-700/50 backdrop-blur-sm border border-slate-700 text-white rounded-lg transition-colors flex items-center gap-2"
            data-testid="admin-button"
          >
            <Settings className="w-4 h-4" />
            Admin
          </Link>
          <Link
            to="/cache"
            className="px-4 py-2 bg-slate-800/50 hover:bg-slate-700/50 backdrop-blur-sm border border-slate-700 text-white rounded-lg transition-colors flex items-center gap-2"
            data-testid="view-cache-button"
          >
            <Database className="w-4 h-4" />
            Cache
          </Link>
          <button
            onClick={() => navigate("/jobs")}
            className="px-4 py-2 bg-slate-800/50 hover:bg-slate-700/50 backdrop-blur-sm border border-slate-700 text-white rounded-lg transition-colors flex items-center gap-2"
            data-testid="view-jobs-button"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            View All Jobs
          </button>
        </div>

        {/* Main Content */}
        <div className="max-w-4xl mx-auto text-center space-y-8">
          {/* Logo/Title */}
          <div className="space-y-4">
            <div className="flex items-center justify-center gap-3 mb-4">
              <Sparkles className="w-10 h-10 text-indigo-400" />
              <h1 className="text-5xl md:text-6xl font-bold tracking-tight text-white">
                Mosaic
              </h1>
            </div>
            <p className="text-xl md:text-2xl text-slate-300 font-light">
              Professional financial models for Indian equities.<br/>
              <span className="text-indigo-400 font-medium">Built by AI. Trusted by analysts.</span>
            </p>
          </div>

          {/* Ticker Input */}
          <div className="max-w-2xl mx-auto">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="relative">
                <input
                  type="text"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  placeholder="Enter NSE/BSE Ticker (e.g., HDFCBANK)"
                  className="ticker-input w-full h-16 bg-slate-900/50 backdrop-blur-md border-2 border-slate-700 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 rounded-lg px-6 text-white placeholder:text-slate-500 transition-all outline-none"
                  disabled={loading}
                  data-testid="ticker-input"
                />
                <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-2">
                  {validating && (
                    <div className="w-5 h-5 border-2 border-indigo-400/30 border-t-indigo-400 rounded-full animate-spin"></div>
                  )}
                  {!validating && isValid === true && ticker.length > 0 && (
                    <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                  {!validating && isValid === false && (
                    <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  )}
                  <Banknote className="w-6 h-6 text-slate-500" />
                </div>
              </div>
              
              {error && (
                <p className="text-red-400 text-sm" data-testid="error-message">{error}</p>
              )}
              
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 disabled:cursor-not-allowed text-white font-semibold px-8 py-4 rounded-lg shadow-[0_0_20px_rgba(99,102,241,0.3)] hover:shadow-[0_0_30px_rgba(99,102,241,0.5)] transition-all duration-200 disabled:shadow-none"
                data-testid="generate-button"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Creating Job...
                  </span>
                ) : (
                  "Generate Model"
                )}
              </button>
            </form>
          </div>

          {/* Features */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 max-w-4xl mx-auto">
            <div className="glass-card p-6 rounded-lg hover:border-slate-600 transition-colors">
              <FileSpreadsheet className="w-8 h-8 text-indigo-400 mb-3" />
              <h3 className="font-semibold text-white mb-2">Complete Excel Model</h3>
              <p className="text-sm text-slate-400">16-sheet workbook with P&L, Balance Sheet, assumptions, and valuation</p>
            </div>
            
            <div className="glass-card p-6 rounded-lg hover:border-slate-600 transition-colors">
              <TrendingUp className="w-8 h-8 text-indigo-400 mb-3" />
              <h3 className="font-semibold text-white mb-2">AI-Powered Analysis</h3>
              <p className="text-sm text-slate-400">Sector-specific reasoning using Claude AI for accurate forecasting</p>
            </div>
            
            <div className="glass-card p-6 rounded-lg hover:border-slate-600 transition-colors">
              <Banknote className="w-8 h-8 text-indigo-400 mb-3" />
              <h3 className="font-semibold text-white mb-2">Investment Thesis</h3>
              <p className="text-sm text-slate-400">Professional-grade research note with recommendation and target price</p>
            </div>
          </div>

          {/* Footer */}
          <p className="text-xs text-slate-500 mt-12">
            Currently supports Banks sector. More sectors coming soon.
          </p>
        </div>
      </div>

      {/* Recent Jobs Section */}
      <div className="relative z-10 px-4 pb-16">
        <div className="max-w-4xl mx-auto">
          <JobsList />
        </div>
      </div>
    </div>
  );
}
