import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { 
  TrendingUp, FileSpreadsheet, Sparkles, Database, Settings, 
  Search, BarChart3, FileText, Brain, BookOpen, AlertCircle,
  Save, Zap, ChevronRight, ArrowUpRight
} from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Tool definitions for the tools section
const MOSAIC_TOOLS = [
  {
    name: "Financial Scraper",
    icon: Database,
    description: "Extracts P&L, Balance Sheet, and quarterly data from Screener.in"
  },
  {
    name: "Market Data",
    icon: TrendingUp,
    description: "Real-time stock prices, P/E, P/B, and market cap via Yahoo Finance"
  },
  {
    name: "PDF Parser",
    icon: FileText,
    description: "Reads investor presentations, annual reports, and concall transcripts"
  },
  {
    name: "Sector Knowledge",
    icon: BookOpen,
    description: "Domain expertise for banking metrics (NIM, CASA, GNPA) and sector benchmarks"
  },
  {
    name: "AI Analysis",
    icon: Brain,
    description: "Claude AI performs valuation, generates thesis, and forecasts assumptions"
  },
  {
    name: "Excel Generator",
    icon: FileSpreadsheet,
    description: "Creates formula-linked 10-sheet workbook with P&L, BS, ROE Tree, Valuation"
  }
];

export default function Landing() {
  const [ticker, setTicker] = useState("");
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [error, setError] = useState("");
  const [isValid, setIsValid] = useState(null);
  const [recentJobs, setRecentJobs] = useState([]);
  const navigate = useNavigate();

  // Fetch recent jobs
  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const response = await axios.get(`${API}/generate/jobs/`);
        setRecentJobs(response.data.slice(0, 5));
      } catch (err) {
        console.error("Failed to fetch jobs:", err);
      }
    };
    fetchJobs();
  }, []);

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

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'text-emerald-400';
      case 'failed': return 'text-red-400';
      case 'processing': return 'text-amber-400';
      default: return 'text-slate-400';
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0e17]">
      {/* Top Navigation Bar */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0a0e17]/80 backdrop-blur-xl border-b border-slate-800/50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-lg flex items-center justify-center">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-white tracking-tight">Mosaic</span>
            <span className="text-xs text-slate-500 ml-2 hidden sm:inline">EQUITY RESEARCH</span>
          </div>
          
          <div className="flex items-center gap-2">
            <Link
              to="/admin"
              className="px-3 py-1.5 text-sm text-slate-400 hover:text-white transition-colors"
            >
              Admin
            </Link>
            <Link
              to="/cache"
              className="px-3 py-1.5 text-sm text-slate-400 hover:text-white transition-colors"
            >
              Cache
            </Link>
            <button
              onClick={() => navigate("/jobs")}
              className="px-4 py-1.5 text-sm bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
            >
              All Jobs
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-16 px-6">
        <div className="max-w-4xl mx-auto text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-full text-emerald-400 text-sm mb-8">
            <Zap className="w-3.5 h-3.5" />
            <span>AI-Powered Financial Modeling</span>
          </div>
          
          {/* Headline */}
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white leading-tight mb-6">
            Professional Financial Models<br/>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">
              Built in Minutes
            </span>
          </h1>
          
          <p className="text-lg text-slate-400 max-w-2xl mx-auto mb-10">
            Enter any NSE/BSE ticker. Our AI agent autonomously scrapes data, analyzes financials, 
            generates valuations, and produces an investment-grade Excel model.
          </p>

          {/* Search Input */}
          <form onSubmit={handleSubmit} className="max-w-xl mx-auto">
            <div className="relative group">
              <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500/20 to-cyan-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all opacity-0 group-hover:opacity-100"></div>
              <div className="relative flex items-center bg-[#111827] border border-slate-700/50 rounded-xl overflow-hidden">
                <div className="pl-5">
                  <Search className="w-5 h-5 text-slate-500" />
                </div>
                <input
                  type="text"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  placeholder="Enter ticker (e.g., HDFCBANK, RELIANCE, TCS)"
                  className="flex-1 bg-transparent px-4 py-4 text-white text-lg placeholder-slate-500 focus:outline-none"
                  data-testid="ticker-input"
                />
                <button
                  type="submit"
                  disabled={loading || isValid === false}
                  className="m-2 px-6 py-2.5 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 disabled:from-slate-600 disabled:to-slate-600 text-white font-medium rounded-lg transition-all flex items-center gap-2"
                  data-testid="generate-button"
                >
                  {loading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                      <span>Analyzing</span>
                    </>
                  ) : (
                    <>
                      <span>Generate Model</span>
                      <ArrowUpRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </div>
            
            {/* Validation Status */}
            <div className="mt-3 h-5 text-sm">
              {validating && (
                <span className="text-slate-500">Validating ticker...</span>
              )}
              {error && (
                <span className="text-red-400">{error}</span>
              )}
              {isValid && !error && ticker && (
                <span className="text-emerald-400">✓ Valid ticker</span>
              )}
            </div>
          </form>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="border-y border-slate-800/50 bg-slate-900/30">
        <div className="max-w-6xl mx-auto px-6 py-8 grid grid-cols-2 md:grid-cols-4 gap-8">
          <div className="text-center">
            <div className="text-3xl font-bold text-white">10+</div>
            <div className="text-sm text-slate-500">Excel Sheets</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-white">5Y</div>
            <div className="text-sm text-slate-500">Forecast Horizon</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-white">6</div>
            <div className="text-sm text-slate-500">AI Tools</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-white">&lt;5min</div>
            <div className="text-sm text-slate-500">Model Generation</div>
          </div>
        </div>
      </section>

      {/* Recent Jobs Section */}
      {recentJobs.length > 0 && (
        <section className="py-16 px-6">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white">Recent Analysis</h2>
              <button 
                onClick={() => navigate("/jobs")}
                className="text-sm text-slate-400 hover:text-emerald-400 transition-colors flex items-center gap-1"
              >
                View All <ChevronRight className="w-4 h-4" />
              </button>
            </div>
            
            <div className="space-y-2">
              {recentJobs.map((job) => (
                <div 
                  key={job.id}
                  onClick={() => job.status === 'completed' ? navigate(`/results/${job.id}`) : navigate(`/processing/${job.id}`)}
                  className="flex items-center justify-between p-4 bg-slate-900/50 hover:bg-slate-800/50 border border-slate-800/50 rounded-xl cursor-pointer transition-all group"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-slate-800 rounded-lg flex items-center justify-center text-white font-mono font-bold">
                      {job.ticker?.slice(0, 2)}
                    </div>
                    <div>
                      <div className="font-medium text-white group-hover:text-emerald-400 transition-colors">
                        {job.ticker}
                      </div>
                      <div className="text-sm text-slate-500">
                        {new Date(job.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className={`text-sm font-medium ${getStatusColor(job.status)}`}>
                      {job.status?.toUpperCase()}
                    </span>
                    <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-emerald-400 transition-colors" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Tools Section */}
      <section className="py-16 px-6 border-t border-slate-800/50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-bold text-white mb-3">Integrated Tools</h2>
            <p className="text-slate-400">Our AI agent orchestrates these specialized tools to build your model</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {MOSAIC_TOOLS.map((tool, index) => (
              <div 
                key={index}
                className="p-5 bg-slate-900/30 border border-slate-800/50 rounded-xl hover:border-emerald-500/30 transition-colors group"
              >
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 bg-emerald-500/10 rounded-lg flex items-center justify-center flex-shrink-0 group-hover:bg-emerald-500/20 transition-colors">
                    <tool.icon className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="font-medium text-white mb-1">{tool.name}</h3>
                    <p className="text-sm text-slate-500 leading-relaxed">{tool.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-slate-800/50">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-slate-500 text-sm">
            <BarChart3 className="w-4 h-4" />
            <span>Mosaic Equity Research</span>
          </div>
          <div className="text-sm text-slate-600">
            Built for investment professionals. Not financial advice.
          </div>
        </div>
      </footer>
    </div>
  );
}
