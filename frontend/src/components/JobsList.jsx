import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, CheckCircle, XCircle, Clock, TrendingUp, RefreshCw, StopCircle } from "lucide-react";
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
  pending: "text-slate-500 bg-slate-500/10",
  processing: "text-indigo-400 bg-indigo-400/10",
  completed: "text-green-500 bg-green-500/10",
  failed: "text-red-500 bg-red-500/10"
};

export default function JobsList() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const navigate = useNavigate();

  const fetchJobs = async (showRefreshing = false) => {
    if (showRefreshing) setRefreshing(true);
    
    try {
      const response = await axios.get(`${API}/generate/jobs?limit=10`);
      setJobs(response.data);
      setLoading(false);
      setRefreshing(false);
    } catch (err) {
      console.error("Failed to fetch jobs:", err);
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    
    // Auto-refresh every 5 seconds if there are processing jobs
    const interval = setInterval(() => {
      const hasProcessing = jobs.some(j => j.status === 'processing');
      if (hasProcessing) {
        fetchJobs();
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

  const handleAbort = async (e, jobId) => {
    e.stopPropagation();
    try {
      await axios.post(`${API}/generate/abort/${jobId}`);
      // Refresh job list
      fetchJobs(true);
    } catch (err) {
      console.error("Abort failed:", err);
    }
  };

  if (loading) {
    return (
      <div className="glass-card p-6 rounded-lg">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
        </div>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="glass-card p-6 rounded-lg">
        <div className="text-center py-8">
          <TrendingUp className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">No jobs yet. Create your first model above!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card p-6 rounded-lg">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-white">Recent Jobs</h2>
          <p className="text-sm text-slate-500">
            {jobs.filter(j => j.status === 'processing').length} running
          </p>
        </div>
        <button
          onClick={() => fetchJobs(true)}
          disabled={refreshing}
          className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
          data-testid="refresh-jobs-button"
        >
          <RefreshCw className={`w-5 h-5 text-slate-400 ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="space-y-3">
        {jobs.map((job) => {
          const StatusIcon = STATUS_ICONS[job.status];
          const statusColorClass = STATUS_COLORS[job.status];
          const progress = job.current_step ? (job.current_step / 8) * 100 : 0;

          return (
            <div
              key={job.id}
              onClick={() => handleJobClick(job)}
              className="border border-slate-700 hover:border-slate-600 rounded-lg p-4 cursor-pointer transition-all hover:bg-slate-800/30"
              data-testid={`job-item-${job.ticker}`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${statusColorClass}`}>
                    <StatusIcon className={`w-5 h-5 ${job.status === 'processing' ? 'animate-spin' : ''}`} />
                  </div>
                  <div>
                    <h3 className="font-mono font-semibold text-white">{job.ticker}</h3>
                    <p className="text-xs text-slate-500">
                      Step {job.current_step || 0}/8
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {job.status === 'failed' && (
                    <button
                      onClick={(e) => handleRetry(e, job.id)}
                      className="px-3 py-1 text-xs bg-indigo-600 hover:bg-indigo-700 text-white rounded transition-colors"
                      data-testid={`retry-${job.ticker}`}
                    >
                      Retry
                    </button>
                  )}
                  <span className={`text-xs px-2 py-1 rounded-full ${statusColorClass} uppercase tracking-wide font-medium`}>
                    {job.status}
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              {job.status === 'processing' && (
                <div className="mt-3">
                  <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-indigo-500 transition-all duration-500"
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {Math.round(progress)}% complete
                  </p>
                </div>
              )}

              {/* Error message */}
              {job.status === 'failed' && job.error && (
                <div className="mt-3 p-2 bg-red-500/10 border border-red-500/20 rounded text-xs text-red-400">
                  {job.error.slice(0, 100)}...
                </div>
              )}

              {/* Completion time */}
              {job.status === 'completed' && (
                <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
                  <CheckCircle className="w-3 h-3 text-green-500" />
                  Click to view results
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
