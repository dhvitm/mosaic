import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { 
  Database, ArrowLeft, Trash2, RefreshCw, ChevronDown, ChevronRight, 
  Check, Clock, FileJson, Building2, TrendingUp, FileSpreadsheet, ScrollText,
  Calculator, BarChart3, MessageSquare
} from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const STEP_ICONS = {
  1: Building2,
  2: BarChart3,
  3: Calculator,
  4: MessageSquare,
  5: TrendingUp,
  6: FileSpreadsheet,
  7: Calculator,
  8: ScrollText
};

const STEP_COLORS = {
  1: "text-blue-400",
  2: "text-green-400",
  3: "text-yellow-400",
  4: "text-purple-400",
  5: "text-orange-400",
  6: "text-cyan-400",
  7: "text-pink-400",
  8: "text-indigo-400"
};

export default function CacheViewer() {
  const { ticker } = useParams();
  const navigate = useNavigate();
  const [cacheData, setCacheData] = useState(null);
  const [allTickers, setAllTickers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedSteps, setExpandedSteps] = useState({});
  const [clearing, setClearing] = useState(false);

  useEffect(() => {
    fetchData();
  }, [ticker]);

  const fetchData = async () => {
    setLoading(true);
    setError("");
    
    try {
      // Always fetch all tickers for sidebar
      const tickersRes = await axios.get(`${API}/generate/cached-tickers`);
      setAllTickers(tickersRes.data.tickers || []);
      
      // If ticker specified, fetch its cache data
      if (ticker) {
        const cacheRes = await axios.get(`${API}/generate/cache/${ticker}`);
        setCacheData(cacheRes.data);
      } else {
        setCacheData(null);
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setError(`No cache found for ${ticker}`);
      } else {
        setError(err.response?.data?.detail || "Failed to fetch cache data");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleClearCache = async () => {
    if (!window.confirm(`Are you sure you want to clear all cached data for ${ticker}?`)) {
      return;
    }
    
    setClearing(true);
    try {
      await axios.delete(`${API}/generate/cache/${ticker}`);
      navigate("/cache");
    } catch (err) {
      setError("Failed to clear cache");
    } finally {
      setClearing(false);
    }
  };

  const toggleStep = (stepNum) => {
    setExpandedSteps(prev => ({
      ...prev,
      [stepNum]: !prev[stepNum]
    }));
  };

  const formatDate = (isoString) => {
    if (!isoString) return "N/A";
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  const renderValue = (value, depth = 0) => {
    if (value === null || value === undefined) {
      return <span className="text-slate-500">null</span>;
    }
    
    if (typeof value === "boolean") {
      return <span className="text-purple-400">{value.toString()}</span>;
    }
    
    if (typeof value === "number") {
      return <span className="text-amber-400">{value}</span>;
    }
    
    if (typeof value === "string") {
      if (value.length > 200) {
        return (
          <span className="text-green-400">
            "{value.slice(0, 200)}..."
            <span className="text-slate-500 text-xs ml-1">({value.length} chars)</span>
          </span>
        );
      }
      return <span className="text-green-400">"{value}"</span>;
    }
    
    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <span className="text-slate-500">[]</span>;
      }
      if (value.length <= 5 && value.every(v => typeof v !== "object")) {
        return (
          <span className="text-slate-300">
            [{value.map((v, i) => (
              <span key={i}>
                {renderValue(v)}
                {i < value.length - 1 && ", "}
              </span>
            ))}]
          </span>
        );
      }
      return (
        <div className="ml-4">
          <span className="text-slate-500">[</span>
          {value.slice(0, 10).map((item, i) => (
            <div key={i} className="ml-2">
              {renderValue(item, depth + 1)}
              {i < Math.min(value.length, 10) - 1 && ","}
            </div>
          ))}
          {value.length > 10 && (
            <div className="text-slate-500 ml-2">... {value.length - 10} more items</div>
          )}
          <span className="text-slate-500">]</span>
        </div>
      );
    }
    
    if (typeof value === "object") {
      const entries = Object.entries(value);
      if (entries.length === 0) {
        return <span className="text-slate-500">{"{}"}</span>;
      }
      return (
        <div className={depth > 0 ? "ml-4" : ""}>
          {entries.slice(0, 20).map(([key, val], i) => (
            <div key={key} className="py-0.5">
              <span className="text-cyan-400">{key}</span>
              <span className="text-slate-500">: </span>
              {renderValue(val, depth + 1)}
            </div>
          ))}
          {entries.length > 20 && (
            <div className="text-slate-500">... {entries.length - 20} more keys</div>
          )}
        </div>
      );
    }
    
    return <span className="text-slate-300">{String(value)}</span>;
  };

  return (
    <div className="min-h-screen bg-slate-950 flex">
      {/* Sidebar */}
      <div className="w-64 bg-slate-900 border-r border-slate-800 p-4 flex flex-col">
        <Link 
          to="/" 
          className="flex items-center gap-2 text-slate-400 hover:text-white mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </Link>
        
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Database className="w-5 h-5 text-indigo-400" />
          Cached Tickers
        </h2>
        
        <div className="flex-1 overflow-y-auto space-y-1">
          {allTickers.length === 0 ? (
            <p className="text-slate-500 text-sm">No cached data</p>
          ) : (
            allTickers.map((t) => (
              <Link
                key={t.ticker}
                to={`/cache/${t.ticker}`}
                className={`block px-3 py-2 rounded-lg transition-colors ${
                  ticker === t.ticker
                    ? "bg-indigo-600 text-white"
                    : "text-slate-300 hover:bg-slate-800"
                }`}
                data-testid={`cache-ticker-${t.ticker}`}
              >
                <div className="font-mono font-semibold">{t.ticker}</div>
                <div className="text-xs text-slate-400">
                  {t.cached_steps} steps cached
                </div>
              </Link>
            ))
          )}
        </div>
        
        <button
          onClick={() => fetchData()}
          className="mt-4 flex items-center justify-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6 overflow-y-auto">
        {!ticker ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Database className="w-16 h-16 text-slate-600 mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Cache Viewer</h2>
            <p className="text-slate-400 max-w-md">
              Select a ticker from the sidebar to view its cached pipeline data.
              Each step's output is stored locally to speed up future runs.
            </p>
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center h-full">
            <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <p className="text-red-400 mb-4">{error}</p>
            <button
              onClick={() => navigate("/cache")}
              className="text-indigo-400 hover:text-indigo-300"
            >
              Back to cache list
            </button>
          </div>
        ) : cacheData ? (
          <div>
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold text-white font-mono">{cacheData.ticker}</h1>
                <p className="text-slate-400">{cacheData.total_steps} steps cached</p>
              </div>
              <button
                onClick={handleClearCache}
                disabled={clearing}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-800 text-white rounded-lg transition-colors"
                data-testid="clear-cache-button"
              >
                <Trash2 className="w-4 h-4" />
                {clearing ? "Clearing..." : "Clear Cache"}
              </button>
            </div>

            {/* Steps */}
            <div className="space-y-4">
              {cacheData.cached_steps.map((step) => {
                const StepIcon = STEP_ICONS[step.step_number] || FileJson;
                const stepColor = STEP_COLORS[step.step_number] || "text-slate-400";
                const isExpanded = expandedSteps[step.step_number];
                
                return (
                  <div 
                    key={step.step_number}
                    className="glass-card rounded-lg overflow-hidden"
                  >
                    {/* Step Header */}
                    <button
                      onClick={() => toggleStep(step.step_number)}
                      className="w-full flex items-center justify-between p-4 hover:bg-slate-800/50 transition-colors"
                      data-testid={`expand-step-${step.step_number}`}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`p-2 rounded-lg bg-slate-800 ${stepColor}`}>
                          <StepIcon className="w-5 h-5" />
                        </div>
                        <div className="text-left">
                          <div className="flex items-center gap-2">
                            <span className="text-white font-semibold">
                              Step {step.step_number}: {step.step_name}
                            </span>
                            <Check className="w-4 h-4 text-green-500" />
                          </div>
                          <div className="text-xs text-slate-500 flex items-center gap-3 mt-1">
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {formatDate(step.cached_at)}
                            </span>
                            <span>{step.size_kb} KB</span>
                          </div>
                        </div>
                      </div>
                      {isExpanded ? (
                        <ChevronDown className="w-5 h-5 text-slate-400" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-slate-400" />
                      )}
                    </button>
                    
                    {/* Step Data */}
                    {isExpanded && (
                      <div className="border-t border-slate-800 p-4 bg-slate-900/50">
                        <div className="font-mono text-sm overflow-x-auto max-h-96 overflow-y-auto">
                          {renderValue(step.data)}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
