import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { 
  Loader2, CheckCircle, XCircle, Circle, 
  Database, Zap, Terminal, Brain, Wrench,
  FileSpreadsheet, Search, BookOpen, AlertCircle, Save,
  TrendingUp, BarChart3, FileText, ArrowRight
} from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const WS_URL = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://');

// Tool configuration with icons and colors
const TOOL_CONFIG = {
  get_screener_financials: { 
    icon: Database, 
    label: "Screener Financials",
    description: "Extracting P&L, Balance Sheet data",
    color: "from-blue-500 to-blue-600"
  },
  get_stock_price: { 
    icon: TrendingUp, 
    label: "Market Data",
    description: "Fetching current price, P/E, P/B",
    color: "from-green-500 to-green-600"
  },
  get_document_links: { 
    icon: FileSpreadsheet, 
    label: "Document Links",
    description: "Finding investor presentations",
    color: "from-purple-500 to-purple-600"
  },
  get_peer_comparison: { 
    icon: BarChart3, 
    label: "Peer Analysis",
    description: "Comparing with sector peers",
    color: "from-orange-500 to-orange-600"
  },
  download_and_parse_pdf: { 
    icon: FileText, 
    label: "PDF Parser",
    description: "Reading investor documents",
    color: "from-pink-500 to-pink-600"
  },
  get_sector_knowledge: { 
    icon: BookOpen, 
    label: "Sector Knowledge",
    description: "Retrieving domain expertise",
    color: "from-cyan-500 to-cyan-600"
  },
  update_sector_knowledge: { 
    icon: Save, 
    label: "Knowledge Update",
    description: "Storing new observations",
    color: "from-teal-500 to-teal-600"
  },
  flag_knowledge_gap: { 
    icon: AlertCircle, 
    label: "Knowledge Gap",
    description: "Flagging missing info",
    color: "from-amber-500 to-amber-600"
  },
  store_analysis_data: { 
    icon: Save, 
    label: "Store Analysis",
    description: "Saving valuation data",
    color: "from-indigo-500 to-indigo-600"
  },
  generate_excel_model: { 
    icon: FileSpreadsheet, 
    label: "Excel Generator",
    description: "Building financial model",
    color: "from-emerald-500 to-emerald-600"
  },
  cache_read: { 
    icon: Database, 
    label: "Cache Read",
    description: "Checking cached data",
    color: "from-slate-500 to-slate-600"
  },
  cache_write: { 
    icon: Save, 
    label: "Cache Write",
    description: "Saving to cache",
    color: "from-slate-500 to-slate-600"
  },
};

// All available tools for the sidebar
const ALL_TOOLS = [
  { id: "get_screener_financials", name: "Screener Financials", icon: Database },
  { id: "get_stock_price", name: "Market Data", icon: TrendingUp },
  { id: "download_and_parse_pdf", name: "PDF Parser", icon: FileText },
  { id: "get_sector_knowledge", name: "Sector Knowledge", icon: BookOpen },
  { id: "store_analysis_data", name: "Analysis Storage", icon: Save },
  { id: "generate_excel_model", name: "Excel Generator", icon: FileSpreadsheet },
];

export default function Processing() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const [retrying, setRetrying] = useState(false);
  const [toolCalls, setToolCalls] = useState([]);
  const [currentTool, setCurrentTool] = useState(null);
  const [usedTools, setUsedTools] = useState(new Set());
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  useEffect(() => {
    let mounted = true;
    
    setJob({
      id: jobId,
      ticker: "",
      status: "processing",
      mode: "agentic",
      current_step: 0,
    });
    
    // Fetch initial job data
    const fetchInitialData = async () => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        const response = await axios.get(`${API}/generate/progress/${jobId}`, {
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (mounted) {
          setJob(response.data);
        }
      } catch (err) {
        console.warn("Initial fetch failed, relying on WebSocket:", err.message);
      }
    };

    fetchInitialData();

    // Connect to WebSocket
    const connectWebSocket = () => {
      const ws = new WebSocket(`${WS_URL}/api/generate/ws/${jobId}`);
      
      ws.onopen = () => {
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);

        switch (message.type) {
          case 'activity_log':
            const activityType = message.activity_type;
            const activityMessage = message.message;
            const details = message.details || {};
            
            if (activityType === 'tool_call') {
              const toolName = details.tool || extractToolName(activityMessage);
              const newTool = {
                id: Date.now(),
                tool: toolName,
                status: 'running',
                message: activityMessage,
                timestamp: new Date().toISOString()
              };
              setToolCalls(prev => [...prev, newTool]);
              setCurrentTool(newTool);
              setUsedTools(prev => new Set([...prev, toolName]));
            } else if (activityType === 'tool_result') {
              setToolCalls(prev => {
                if (prev.length === 0) return prev;
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  status: details.success ? 'completed' : 'failed',
                  duration: details.duration
                };
                return updated;
              });
              setCurrentTool(null);
            } else if (activityType === 'agent_start') {
              if (details.ticker) {
                setJob(prev => ({ ...prev, ticker: details.ticker }));
              }
            } else if (activityType === 'agent_complete') {
              setJob(prev => ({ ...prev, status: 'completed' }));
            }
            break;

          case 'job_status':
            setJob((prevJob) => ({
              ...prevJob,
              status: message.status,
              current_step: message.current_step,
            }));
            break;

          case 'job_complete':
            setJob((prevJob) => ({
              ...prevJob,
              status: 'completed',
            }));
            setTimeout(() => {
              navigate(`/results/${jobId}`);
            }, 1500);
            break;

          case 'error':
            setError(message.error);
            setJob((prevJob) => ({
              ...prevJob,
              status: 'failed'
            }));
            break;

          default:
            break;
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket closed, attempting to reconnect...');
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket();
        }, 3000);
      };

      wsRef.current = ws;
    };

    connectWebSocket();

    return () => {
      mounted = false;
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [jobId, navigate]);

  const extractToolName = (message) => {
    const toolPatterns = {
      'financial statements': 'get_screener_financials',
      'stock price': 'get_stock_price',
      'document links': 'get_document_links',
      'peer': 'get_peer_comparison',
      'Reading': 'download_and_parse_pdf',
      'PDF': 'download_and_parse_pdf',
      'sector knowledge': 'get_sector_knowledge',
      'Updating knowledge': 'update_sector_knowledge',
      'Knowledge gap': 'flag_knowledge_gap',
      'Excel': 'generate_excel_model',
      'Building Excel': 'generate_excel_model',
      'Storing': 'store_analysis_data',
      'cache': 'cache_read',
      'Caching': 'cache_write',
    };
    
    for (const [pattern, tool] of Object.entries(toolPatterns)) {
      if (message.toLowerCase().includes(pattern.toLowerCase())) {
        return tool;
      }
    }
    return 'unknown';
  };

  const handleRetry = async () => {
    setRetrying(true);
    try {
      const response = await axios.post(`${API}/generate/retry/${jobId}`);
      const newJobId = response.data.new_job_id;
      navigate(`/processing/${newJobId}`);
    } catch (err) {
      console.error("Retry failed:", err);
      setError("Failed to retry job");
      setRetrying(false);
    }
  };

  if (error && job?.status === 'failed') {
    return (
      <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-slate-900 border border-slate-800 p-8 rounded-xl text-center">
          <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-white mb-2">Analysis Failed</h2>
          <p className="text-slate-400 mb-6">{error}</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={handleRetry}
              disabled={retrying}
              className="bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-700 text-white px-6 py-2 rounded-lg transition-colors flex items-center gap-2"
            >
              {retrying ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : null}
              Retry Analysis
            </button>
            <button
              onClick={() => navigate("/")}
              className="bg-slate-700 hover:bg-slate-600 text-white px-6 py-2 rounded-lg transition-colors"
            >
              Go Home
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-emerald-400 animate-spin" />
      </div>
    );
  }

  const completedTools = toolCalls.filter(t => t.status === 'completed').length;

  return (
    <div className="min-h-screen bg-[#0a0e17]">
      {/* Header */}
      <header className="bg-[#0a0e17]/80 backdrop-blur-xl border-b border-slate-800/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-lg flex items-center justify-center">
                <BarChart3 className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white flex items-center gap-3">
                  Analyzing
                  <span className="text-emerald-400 font-mono">{job.ticker || '...'}</span>
                  {job.status === 'completed' && (
                    <span className="text-sm bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded">COMPLETE</span>
                  )}
                </h1>
                <p className="text-sm text-slate-500">AI agent building financial model</p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-mono font-bold text-emerald-400">
                {completedTools}
              </div>
              <div className="text-xs text-slate-500">Tools Used</div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          
          {/* Tools Sidebar */}
          <div className="lg:col-span-1">
            <div className="sticky top-24">
              <h3 className="text-sm font-medium text-slate-400 mb-4 uppercase tracking-wider">Available Tools</h3>
              <div className="space-y-2">
                {ALL_TOOLS.map((tool) => {
                  const isUsed = usedTools.has(tool.id);
                  const isActive = currentTool?.tool === tool.id;
                  const ToolIcon = tool.icon;
                  
                  return (
                    <div 
                      key={tool.id}
                      className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${
                        isActive 
                          ? 'bg-emerald-500/10 border-emerald-500/50' 
                          : isUsed 
                            ? 'bg-slate-800/50 border-slate-700/50' 
                            : 'bg-slate-900/30 border-slate-800/30'
                      }`}
                    >
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                        isActive 
                          ? 'bg-emerald-500/20' 
                          : isUsed 
                            ? 'bg-slate-700/50' 
                            : 'bg-slate-800/50'
                      }`}>
                        {isActive ? (
                          <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
                        ) : isUsed ? (
                          <CheckCircle className="w-4 h-4 text-emerald-400" />
                        ) : (
                          <ToolIcon className="w-4 h-4 text-slate-500" />
                        )}
                      </div>
                      <span className={`text-sm ${
                        isActive 
                          ? 'text-emerald-400 font-medium' 
                          : isUsed 
                            ? 'text-white' 
                            : 'text-slate-500'
                      }`}>
                        {tool.name}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Main Content - Tool Calls */}
          <div className="lg:col-span-3">
            <h3 className="text-sm font-medium text-slate-400 mb-4 uppercase tracking-wider">Execution Log</h3>
            
            {toolCalls.length === 0 ? (
              <div className="bg-slate-900/30 border border-slate-800/50 rounded-xl p-12 text-center">
                <div className="w-16 h-16 bg-slate-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Brain className="w-8 h-8 text-slate-600 animate-pulse" />
                </div>
                <h3 className="text-lg font-medium text-white mb-2">Agent Initializing</h3>
                <p className="text-slate-500">Tools will appear here as they are invoked...</p>
              </div>
            ) : (
              <div className="space-y-3">
                {toolCalls.map((call, index) => {
                  const config = TOOL_CONFIG[call.tool] || { 
                    icon: Wrench, 
                    label: call.tool,
                    description: call.message,
                    color: "from-slate-500 to-slate-600"
                  };
                  const ToolIcon = config.icon;
                  const isRunning = call.status === 'running';
                  const isCompleted = call.status === 'completed';
                  const isFailed = call.status === 'failed';
                  
                  return (
                    <div 
                      key={call.id}
                      className={`flex items-center gap-4 p-4 rounded-xl border transition-all ${
                        isRunning 
                          ? 'bg-slate-800/80 border-emerald-500/50 shadow-lg shadow-emerald-500/10' 
                          : isCompleted
                            ? 'bg-slate-900/50 border-slate-800/50'
                            : isFailed
                              ? 'bg-red-950/30 border-red-500/30'
                              : 'bg-slate-900/30 border-slate-800/30'
                      }`}
                      data-testid={`tool-call-${index}`}
                    >
                      {/* Tool Icon */}
                      <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${config.color} flex items-center justify-center flex-shrink-0 ${
                        isRunning ? 'animate-pulse' : ''
                      }`}>
                        <ToolIcon className="w-6 h-6 text-white" />
                      </div>
                      
                      {/* Tool Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium text-white">{config.label}</h4>
                          {isRunning && (
                            <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full animate-pulse">
                              RUNNING
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-slate-500 truncate">{config.description}</p>
                      </div>
                      
                      {/* Status */}
                      <div className="flex-shrink-0 flex items-center gap-3">
                        {call.duration && (
                          <span className="text-xs text-slate-500 font-mono">
                            {call.duration.toFixed(1)}s
                          </span>
                        )}
                        {isRunning && (
                          <Loader2 className="w-5 h-5 text-emerald-400 animate-spin" />
                        )}
                        {isCompleted && (
                          <CheckCircle className="w-5 h-5 text-emerald-400" />
                        )}
                        {isFailed && (
                          <XCircle className="w-5 h-5 text-red-400" />
                        )}
                      </div>
                    </div>
                  );
                })}
                
                {/* Completion Message */}
                {job.status === 'completed' && (
                  <div className="mt-6 p-6 bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 border border-emerald-500/30 rounded-xl">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-emerald-500/20 rounded-full flex items-center justify-center">
                          <CheckCircle className="w-6 h-6 text-emerald-400" />
                        </div>
                        <div>
                          <h3 className="text-lg font-medium text-white">Analysis Complete</h3>
                          <p className="text-sm text-slate-400">Redirecting to results...</p>
                        </div>
                      </div>
                      <button
                        onClick={() => navigate(`/results/${jobId}`)}
                        className="flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-white rounded-lg transition-colors"
                      >
                        View Results
                        <ArrowRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
