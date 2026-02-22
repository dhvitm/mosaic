import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { 
  Loader2, CheckCircle, XCircle, AlertTriangle, Circle, 
  Cpu, Database, Zap, Info, Terminal, Brain, Wrench,
  FileSpreadsheet, Search, BookOpen, AlertCircle, Save,
  TrendingUp, MessageSquare
} from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const WS_URL = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://');

// Tool icons mapping for agent tools
const TOOL_ICONS = {
  get_screener_financials: Database,
  get_stock_price: TrendingUp,
  get_document_links: FileSpreadsheet,
  get_peer_comparison: Search,
  download_and_parse_pdf: FileSpreadsheet,
  get_sector_knowledge: BookOpen,
  update_sector_knowledge: Save,
  flag_knowledge_gap: AlertCircle,
  write_excel_model: FileSpreadsheet,
  cache_read: Database,
  cache_write: Save,
};

// Tool descriptions for better UX
const TOOL_DESCRIPTIONS = {
  get_screener_financials: "Fetching financial statements",
  get_stock_price: "Getting current stock price",
  get_document_links: "Finding investor documents",
  get_peer_comparison: "Comparing with peers",
  download_and_parse_pdf: "Reading document",
  get_sector_knowledge: "Consulting sector knowledge",
  update_sector_knowledge: "Updating knowledge base",
  flag_knowledge_gap: "Flagging knowledge gap",
  write_excel_model: "Building Excel model",
  cache_read: "Checking cache",
  cache_write: "Saving to cache",
};

const ACTIVITY_ICONS = {
  api_call: Zap,
  llm_thinking: Brain,
  data_processing: Database,
  info: Info,
  error: XCircle,
  tool_call: Wrench,
  tool_result: CheckCircle,
  agent_start: Brain,
  agent_complete: CheckCircle,
  success: CheckCircle
};

const ACTIVITY_COLORS = {
  api_call: "text-amber-400",
  llm_thinking: "text-purple-400",
  data_processing: "text-blue-400",
  info: "text-slate-400",
  error: "text-red-400",
  tool_call: "text-indigo-400",
  tool_result: "text-green-400",
  agent_start: "text-purple-500",
  agent_complete: "text-green-500",
  success: "text-green-400"
};

export default function Processing() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const [retrying, setRetrying] = useState(false);
  const [activityLog, setActivityLog] = useState([]);
  const [toolCalls, setToolCalls] = useState([]);
  const [agentThinking, setAgentThinking] = useState("");
  const [currentLoop, setCurrentLoop] = useState(0);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const activityLogRef = useRef(null);
  const toolsRef = useRef(null);

  useEffect(() => {
    let mounted = true;
    
    // Start with minimal job data for agentic mode
    setJob({
      id: jobId,
      ticker: "",
      status: "processing",
      mode: "agentic",
      current_step: 0,
      steps: []
    });
    
    // Fetch initial job data in background
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

    // Connect to WebSocket for real-time updates
    const connectWebSocket = () => {
      const ws = new WebSocket(`${WS_URL}/api/generate/ws/${jobId}`);
      
      ws.onopen = () => {
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('WebSocket message:', message);

        switch (message.type) {
          case 'connected':
            console.log('WebSocket connection confirmed');
            break;

          case 'activity_log':
            const activityType = message.activity_type;
            const activityMessage = message.message;
            const details = message.details || {};
            
            // Track tool calls separately for the tools panel
            if (activityType === 'tool_call') {
              const toolName = details.tool || extractToolName(activityMessage);
              setToolCalls(prev => [...prev, {
                id: Date.now(),
                tool: toolName,
                status: 'running',
                message: activityMessage,
                timestamp: new Date().toISOString()
              }]);
            } else if (activityType === 'tool_result') {
              // Update last tool call status
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
            } else if (activityType === 'agent_start') {
              setAgentThinking("Initializing analysis...");
              if (details.ticker) {
                setJob(prev => ({ ...prev, ticker: details.ticker }));
              }
            } else if (activityType === 'agent_complete') {
              setAgentThinking("Analysis complete!");
              if (details.iterations) {
                setCurrentLoop(details.iterations);
              }
            }
            
            // Add to activity log
            setActivityLog((prev) => {
              const newLog = [...prev, {
                id: Date.now(),
                activity_type: activityType,
                message: activityMessage,
                details: details,
                timestamp: message.timestamp || new Date().toISOString()
              }];
              return newLog.slice(-100);
            });
            
            // Auto-scroll activity log
            setTimeout(() => {
              if (activityLogRef.current) {
                activityLogRef.current.scrollTop = activityLogRef.current.scrollHeight;
              }
            }, 100);
            break;

          case 'job_status':
            setJob((prevJob) => ({
              ...prevJob,
              status: message.status,
              current_step: message.current_step,
              reasoning: message.reasoning
            }));
            break;

          case 'job_complete':
            setJob((prevJob) => ({
              ...prevJob,
              status: 'completed',
              result: message.result,
              reasoning: message.reasoning
            }));
            
            // Navigate to results after a short delay
            setTimeout(() => {
              navigate(`/results/${jobId}`);
            }, 2000);
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
    // Extract tool name from message like "📊 Pulling financial statements..."
    const toolPatterns = {
      'financial statements': 'get_screener_financials',
      'stock price': 'get_stock_price',
      'document links': 'get_document_links',
      'peer comparison': 'get_peer_comparison',
      'Reading': 'download_and_parse_pdf',
      'sector knowledge': 'get_sector_knowledge',
      'Updating knowledge': 'update_sector_knowledge',
      'Knowledge gap': 'flag_knowledge_gap',
      'Excel model': 'write_excel_model',
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
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="max-w-md w-full glass-card p-8 rounded-lg text-center">
          <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-white mb-2">Analysis Failed</h2>
          <p className="text-slate-400 mb-2">{error}</p>
          <p className="text-sm text-slate-500 mb-6">
            The agent encountered an error. You can retry the analysis.
          </p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={handleRetry}
              disabled={retrying}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 text-white px-6 py-2 rounded-lg transition-colors flex items-center gap-2"
              data-testid="retry-button"
            >
              {retrying ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Retrying...
                </>
              ) : (
                <>Retry Analysis</>
              )}
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
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-indigo-400 animate-spin" />
      </div>
    );
  }

  const completedTools = toolCalls.filter(t => t.status === 'completed').length;
  const totalTools = toolCalls.length;

  return (
    <div className="min-h-screen bg-slate-950 p-4 md:p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="glass-card p-6 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative">
                <Brain className="w-12 h-12 text-indigo-400" />
                <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-500 rounded-full animate-pulse border-2 border-slate-900"></div>
              </div>
              <div>
                <h1 className="text-2xl md:text-3xl font-bold text-white">
                  Mosaic Agent Analyzing: <span className="text-indigo-400">{job.ticker || '...'}</span>
                </h1>
                <p className="text-slate-400 mt-1">
                  Autonomous financial analysis in progress
                </p>
              </div>
            </div>
            <div className="text-right hidden md:block">
              <div className="text-sm text-slate-500">Agent Loop</div>
              <div className="text-2xl font-mono font-bold text-indigo-400">
                #{currentLoop || toolCalls.length > 0 ? Math.ceil(toolCalls.length / 3) : 0}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Panel - Agent Tools */}
        <div className="glass-card p-6 rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Wrench className="w-5 h-5 text-indigo-400" />
              <h2 className="text-lg font-semibold text-white">Tool Invocations</h2>
            </div>
            <div className="text-sm text-slate-500">
              {completedTools}/{totalTools} completed
            </div>
          </div>
          
          <div 
            ref={toolsRef}
            className="h-[400px] overflow-y-auto space-y-3 pr-2"
            data-testid="tool-calls-panel"
          >
            {toolCalls.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center text-slate-500">
                  <Wrench className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>Agent is initializing...</p>
                  <p className="text-sm mt-1">Tools will appear as they are invoked</p>
                </div>
              </div>
            ) : (
              toolCalls.map((tool, index) => {
                const ToolIcon = TOOL_ICONS[tool.tool] || Wrench;
                const isRunning = tool.status === 'running';
                const isCompleted = tool.status === 'completed';
                const isFailed = tool.status === 'failed';
                
                return (
                  <div 
                    key={tool.id}
                    className={`p-4 rounded-lg border transition-all ${
                      isRunning 
                        ? 'bg-indigo-950/50 border-indigo-500/50 animate-pulse' 
                        : isCompleted
                          ? 'bg-slate-800/50 border-green-500/30'
                          : isFailed
                            ? 'bg-red-950/30 border-red-500/30'
                            : 'bg-slate-800/30 border-slate-700/50'
                    }`}
                    data-testid={`tool-call-${index}`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg ${
                        isRunning ? 'bg-indigo-500/20' : 
                        isCompleted ? 'bg-green-500/20' : 
                        isFailed ? 'bg-red-500/20' : 'bg-slate-700/50'
                      }`}>
                        {isRunning ? (
                          <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
                        ) : isCompleted ? (
                          <CheckCircle className="w-5 h-5 text-green-400" />
                        ) : isFailed ? (
                          <XCircle className="w-5 h-5 text-red-400" />
                        ) : (
                          <ToolIcon className="w-5 h-5 text-slate-400" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <h4 className={`font-medium ${
                            isRunning ? 'text-indigo-300' : 
                            isCompleted ? 'text-white' : 
                            'text-slate-400'
                          }`}>
                            {TOOL_DESCRIPTIONS[tool.tool] || tool.tool}
                          </h4>
                          {tool.duration && (
                            <span className="text-xs text-slate-500">
                              {tool.duration.toFixed(1)}s
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-slate-500 mt-1 truncate">
                          {tool.message}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Panel - Activity Stream */}
        <div className="glass-card p-6 rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Terminal className="w-5 h-5 text-indigo-400" />
              <h2 className="text-lg font-semibold text-white">Live Activity Stream</h2>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs text-slate-500">Streaming</span>
            </div>
          </div>
          
          <div 
            ref={activityLogRef}
            className="h-[400px] overflow-y-auto bg-slate-900/50 rounded-lg p-4 font-mono text-sm space-y-2"
            data-testid="activity-log"
          >
            {activityLog.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center text-slate-500">
                  <Brain className="w-12 h-12 mx-auto mb-3 opacity-30 animate-pulse" />
                  <p>Connecting to agent...</p>
                </div>
              </div>
            ) : (
              activityLog.map((entry) => {
                const ActivityIcon = ACTIVITY_ICONS[entry.activity_type] || Info;
                const colorClass = ACTIVITY_COLORS[entry.activity_type] || "text-slate-400";
                const time = new Date(entry.timestamp).toLocaleTimeString();
                
                return (
                  <div 
                    key={entry.id} 
                    className="flex items-start gap-3 py-2 border-b border-slate-800/50 last:border-0"
                  >
                    <ActivityIcon className={`w-4 h-4 flex-shrink-0 mt-0.5 ${colorClass}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-slate-300 break-words text-xs md:text-sm">{entry.message}</p>
                      {entry.details?.iterations && (
                        <p className="text-xs text-slate-500 mt-1">
                          Completed in {entry.details.iterations} iterations, {entry.details.tool_calls} tool calls
                        </p>
                      )}
                    </div>
                    <span className="text-xs text-slate-600 flex-shrink-0">{time}</span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Agent Status Bar */}
      <div className="max-w-7xl mx-auto mt-6">
        <div className="glass-card p-4 rounded-lg">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Brain className="w-5 h-5 text-purple-400" />
                <span className="text-sm text-slate-400">Agent Status:</span>
                <span className={`text-sm font-medium ${
                  job.status === 'completed' ? 'text-green-400' :
                  job.status === 'failed' ? 'text-red-400' :
                  'text-indigo-400'
                }`}>
                  {job.status === 'completed' ? 'Analysis Complete' :
                   job.status === 'failed' ? 'Failed' :
                   'Analyzing...'}
                </span>
              </div>
            </div>
            
            <div className="flex items-center gap-6 text-sm">
              <div className="flex items-center gap-2">
                <Wrench className="w-4 h-4 text-indigo-400" />
                <span className="text-slate-500">Tools Used:</span>
                <span className="text-white font-medium">{completedTools}</span>
              </div>
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-amber-400" />
                <span className="text-slate-500">Activities:</span>
                <span className="text-white font-medium">{activityLog.length}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="max-w-7xl mx-auto mt-4">
        <div className="flex flex-wrap justify-center gap-4 text-xs text-slate-500">
          <div className="flex items-center gap-1.5">
            <Wrench className="w-3 h-3 text-indigo-400" />
            <span>Tool Call</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle className="w-3 h-3 text-green-400" />
            <span>Success</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Brain className="w-3 h-3 text-purple-400" />
            <span>AI Thinking</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Database className="w-3 h-3 text-blue-400" />
            <span>Data Processing</span>
          </div>
        </div>
      </div>
    </div>
  );
}
