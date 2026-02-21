import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Loader2, CheckCircle, XCircle, AlertTriangle, Circle } from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const STEP_ICONS = {
  pending: Circle,
  in_progress: Loader2,
  completed: CheckCircle,
  error: XCircle,
  warning: AlertTriangle
};

const STEP_COLORS = {
  pending: "text-slate-600",
  in_progress: "text-indigo-400 animate-pulse",
  completed: "text-green-500",
  error: "text-red-500",
  warning: "text-yellow-500"
};

export default function Processing() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const pollProgress = async () => {
      try {
        const response = await axios.get(`${API}/generate/progress/${jobId}`);
        setJob(response.data);

        if (response.data.status === "completed") {
          setTimeout(() => {
            navigate(`/results/${jobId}`);
          }, 1500);
        } else if (response.data.status === "failed") {
          setError(response.data.error || "Job failed");
        }
      } catch (err) {
        setError(err.response?.data?.detail || "Failed to fetch job progress");
      }
    };

    // Initial fetch
    pollProgress();

    // Poll every 2 seconds
    const interval = setInterval(pollProgress, 2000);

    return () => clearInterval(interval);
  }, [jobId, navigate]);

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="max-w-md w-full glass-card p-8 rounded-lg text-center">
          <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-white mb-2">Error</h2>
          <p className="text-slate-400 mb-6">{error}</p>
          <button
            onClick={() => navigate("/")}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-indigo-400 animate-spin" />
      </div>
    );
  }

  const progress = job.steps.length > 0 
    ? (job.steps.filter(s => s.status === 'completed').length / job.steps.length) * 100 
    : 0;

  return (
    <div className="min-h-screen bg-slate-950 p-4 md:p-8">
      {/* Header */}
      <div className="max-w-6xl mx-auto mb-8">
        <div className="glass-card p-6 rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-white mb-1">
                Generating Model: {job.ticker}
              </h1>
              <p className="text-slate-400">
                {job.result?.company_metadata?.full_name || "Processing..."}
              </p>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold font-mono text-indigo-400">
                {Math.round(progress)}%
              </div>
              <div className="text-sm text-slate-500">Complete</div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
            <div 
              className="h-full bg-indigo-500 transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            ></div>
          </div>

          {/* Time Estimate */}
          <div className="mt-4 text-sm text-slate-500">
            Estimated time: 4-6 minutes
          </div>
        </div>
      </div>

      {/* Pipeline Steps */}
      <div className="max-w-6xl mx-auto">
        <div className="glass-card p-8 rounded-lg">
          <h2 className="text-xl font-semibold text-white mb-6">Pipeline Status</h2>
          
          <div className="space-y-6">
            {job.steps.map((step, index) => {
              const Icon = STEP_ICONS[step.status];
              const colorClass = STEP_COLORS[step.status];
              
              return (
                <div 
                  key={index}
                  className="flex items-start gap-4 group"
                  data-testid={`step-${step.step_number}`}
                >
                  {/* Icon */}
                  <div className={`flex-shrink-0 ${colorClass}`}>
                    <Icon className={`w-6 h-6 ${step.status === 'in_progress' ? 'animate-spin' : ''}`} />
                  </div>

                  {/* Content */}
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <h3 className={`font-medium ${
                        step.status === 'completed' ? 'text-white' : 
                        step.status === 'in_progress' ? 'text-indigo-300' : 
                        'text-slate-500'
                      }`}>
                        Step {step.step_number}: {step.name}
                      </h3>
                      <span className={`text-xs uppercase tracking-wide ${colorClass}`}>
                        {step.status.replace('_', ' ')}
                      </span>
                    </div>
                    
                    {step.message && (
                      <p className="text-sm text-slate-400">{step.message}</p>
                    )}
                    
                    {step.status === 'in_progress' && (
                      <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
                        <div className="flex gap-1">
                          <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                          <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                          <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                        </div>
                        Processing...
                      </div>
                    )}
                  </div>

                  {/* Vertical Line */}
                  {index < job.steps.length - 1 && (
                    <div className="absolute left-[27px] mt-8 w-0.5 h-10 bg-slate-800"></div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Footer Message */}
      {job.status === 'processing' && (
        <div className="max-w-6xl mx-auto mt-6 text-center">
          <p className="text-slate-500 text-sm">
            Please wait while we generate your financial model. This page will automatically update.
          </p>
        </div>
      )}
    </div>
  );
}
