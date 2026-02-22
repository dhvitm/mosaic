import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, CheckCircle, XCircle, Clock, ArrowLeft, Database, RefreshCw, StopCircle } from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const STATUS_ICONS = {
  pending: Clock,
  processing: Loader2,
  completed: CheckCircle,
  failed: XCircle
};

const STATUS_COLORS = {
  pending: "text-slate-500 bg-slate-500/10 border-slate-500/20",
  processing: "text-indigo-400 bg-indigo-400/10 border-indigo-400/20",
  completed: "text-green-500 bg-green-500/10 border-green-500/20",
  failed: "text-red-500 bg-red-500/10 border-red-500/20"
};

export default function Jobs() {
  const [jobs, setJobs] = useState([]);
  const [cachedTickers, setCachedTickers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const navigate = useNavigate();

  const fetchData = async () => {
    try {
      const [jobsResponse, cacheResponse] = await Promise.all([
        axios.get(`${API}/generate/jobs?limit=20`),
        axios.get(`${API}/generate/cached-tickers`)
      ]);
      
      setJobs(jobsResponse.data);
      setCachedTickers(cacheResponse.data.tickers || []);
      setLoading(false);
      setRefreshing(false);
    } catch (err) {
      console.error("Failed to fetch data:", err);
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    
    // Auto-refresh every 5 seconds
    const interval = setInterval(() => {
      const hasProcessing = jobs.some(j => j.status === 'processing');
      if (hasProcessing) {
        fetchData();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [jobs]);

  const handleJobClick = (job) => {
    if (job.status === 'completed') {
      navigate(`/results/${job.id}`);
    } else {
      navigate(`/processing/${job.id}`);
    }
  };

  const handleRetry = async (e, jobId) => {
    e.stopPropagation();
    try {
      const response = await axios.post(`${API}/generate/retry/${jobId}`);
      navigate(`/processing/${response.data.new_job_id}`);
    } catch (err) {
      console.error("Retry failed:", err);
    }
  };

  const handleAbort = async (e, jobId, ticker) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to abort the job for ${ticker}?`)) {
      return;
    }
    try {
      await axios.post(`${API}/generate/abort/${jobId}`);
      // Refresh job list
      fetchData();
    } catch (err) {
      console.error("Abort failed:", err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-indigo-400 animate-spin" />
      </div>
    );
  }

  const processingJobs = jobs.filter(j => j.status === 'processing');
  const completedJobs = jobs.filter(j => j.status === 'completed');
  const failedJobs = jobs.filter(j => j.status === 'failed');

  return (
    <div className="min-h-screen bg-slate-950 p-4 md:p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2 text-slate-400 hover:text-white mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </button>

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">All Jobs</h1>
            <p className="text-slate-400">
              {processingJobs.length} running • {completedJobs.length} completed • {failedJobs.length} failed
            </p>
          </div>
          <button
            onClick={() => {
              setRefreshing(true);
              fetchData();
            }}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Jobs List */}
        <div className="lg:col-span-2 space-y-4">
          {jobs.map((job) => {
            const StatusIcon = STATUS_ICONS[job.status];
            const statusColorClass = STATUS_COLORS[job.status];
            const progress = job.current_step ? (job.current_step / 8) * 100 : 0;

            return (
              <div
                key={job.id}
                onClick={() => handleJobClick(job)}
                className="glass-card p-6 rounded-lg cursor-pointer hover:border-slate-600 transition-all"
                data-testid={`job-${job.ticker}`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-start gap-4">
                    <div className={`p-3 rounded-lg border ${statusColorClass}`}>
                      <StatusIcon className={`w-6 h-6 ${job.status === 'processing' ? 'animate-spin' : ''}`} />
                    </div>
                    <div>
                      <h3 className="text-2xl font-mono font-bold text-white mb-1">{job.ticker}</h3>
                      <p className="text-sm text-slate-400">
                        Created {new Date(job.created_at).toLocaleString()}
                      </p>
                      <div className="mt-2">
                        <span className={`text-xs px-3 py-1 rounded-full border ${statusColorClass} uppercase tracking-wide font-medium`}>
                          {job.status}
                        </span>
                      </div>
                    </div>
                  </div>

                  {job.status === 'failed' && (
                    <button
                      onClick={(e) => handleRetry(e, job.id)}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors flex items-center gap-2"
                    >
                      <RefreshCw className="w-4 h-4" />
                      Retry
                    </button>
                  )}
                </div>

                {/* Progress */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-400">
                      Step {job.current_step || 0}/8
                    </span>
                    <span className="font-mono text-indigo-400">
                      {Math.round(progress)}%
                    </span>
                  </div>
                  <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-indigo-500 transition-all duration-500"
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>
                </div>

                {/* Error */}
                {job.status === 'failed' && job.error && (
                  <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded text-sm text-red-400">
                    <strong>Error:</strong> {job.error.slice(0, 150)}...
                  </div>
                )}
              </div>
            );
          })}

          {jobs.length === 0 && (
            <div className="glass-card p-12 rounded-lg text-center">
              <Database className="w-16 h-16 text-slate-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">No Jobs Yet</h3>
              <p className="text-slate-400 mb-6">Create your first model to get started</p>
              <button
                onClick={() => navigate("/")}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg transition-colors"
              >
                Create Model
              </button>
            </div>
          )}
        </div>

        {/* Cache Status Sidebar */}
        <div className="space-y-4">
          <div className="glass-card p-6 rounded-lg">
            <h2 className="text-lg font-semibold text-white mb-4">Cached Data</h2>
            
            {cachedTickers.length === 0 ? (
              <p className="text-sm text-slate-500">No cached data yet</p>
            ) : (
              <div className="space-y-3">
                {cachedTickers.map((item) => (
                  <div
                    key={item.ticker}
                    className="p-3 bg-slate-800/50 rounded-lg border border-slate-700"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono font-semibold text-white">{item.ticker}</span>
                      <span className="text-xs text-indigo-400">{item.cached_steps} steps</span>
                    </div>
                    <p className="text-xs text-slate-500">
                      {new Date(item.last_updated * 1000).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Stats */}
          <div className="glass-card p-6 rounded-lg">
            <h2 className="text-lg font-semibold text-white mb-4">Statistics</h2>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Total Jobs</span>
                <span className="font-semibold text-white">{jobs.length}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Processing</span>
                <span className="font-semibold text-indigo-400">{processingJobs.length}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Completed</span>
                <span className="font-semibold text-green-500">{completedJobs.length}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Failed</span>
                <span className="font-semibold text-red-500">{failedJobs.length}</span>
              </div>
              <div className="flex justify-between items-center pt-3 border-t border-slate-700">
                <span className="text-slate-400">Cached Tickers</span>
                <span className="font-semibold text-white">{cachedTickers.length}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
