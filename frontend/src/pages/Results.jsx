import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Download, TrendingUp, TrendingDown, Minus, ScrollText, SlidersHorizontal, Grid3X3, Loader2, Brain, ChevronDown, ChevronUp } from "lucide-react";
import axios from "axios";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Results() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState("");
  const [showReasoning, setShowReasoning] = useState(false);

  useEffect(() => {
    const fetchResult = async () => {
      try {
        const response = await axios.get(`${API}/generate/result/${jobId}`);
        setResult(response.data);
        setLoading(false);
      } catch (err) {
        setError(err.response?.data?.detail || "Failed to fetch results");
        setLoading(false);
      }
    };

    fetchResult();
  }, [jobId]);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const response = await axios.get(`${API}/generate/download/${jobId}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${result.ticker}_model.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      setDownloading(false);
    } catch (err) {
      setError("Failed to download Excel file");
      setDownloading(false);
    }
  };

  const handleRetry = async () => {
    setRetrying(true);
    try {
      const response = await axios.post(`${API}/generate/retry/${jobId}`);
      const newJobId = response.data.new_job_id;
      
      // Navigate to the new job's processing page
      navigate(`/processing/${newJobId}`);
    } catch (err) {
      setError("Failed to retry job");
      setRetrying(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-indigo-400 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="max-w-md w-full glass-card p-8 rounded-lg text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={() => navigate("/")}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg transition-colors"
          >
            Go Home
          </button>
        </div>
      </div>
    );
  }

  const valuation = result.result?.valuation || {};
  const thesis = result.result?.thesis || {};
  const metadata = result.result?.company_metadata || {};
  
  const recommendation = valuation.recommendation || "HOLD";
  const recClass = recommendation === "BUY" ? "recommendation-buy" : 
                   recommendation === "SELL" ? "recommendation-sell" : 
                   "recommendation-hold";
  const recColor = recommendation === "BUY" ? "text-green-500" : 
                   recommendation === "SELL" ? "text-red-500" : 
                   "text-yellow-500";
  const RecIcon = recommendation === "BUY" ? TrendingUp : 
                  recommendation === "SELL" ? TrendingDown : 
                  Minus;

  return (
    <div className="min-h-screen bg-slate-950 p-4 md:p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-white mb-1 font-mono">
              {result.ticker}
            </h1>
            <p className="text-slate-400">{metadata.full_name || "Company Analysis"}</p>
          </div>
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 text-white px-6 py-3 rounded-lg flex items-center gap-2 shadow-lg transition-all"
            data-testid="download-excel-button"
          >
            {downloading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Downloading...
              </>
            ) : (
              <>
                <Download className="w-5 h-5" />
                Download Excel
              </>
            )}
          </button>
        </div>
      </div>

      {/* Recommendation Box */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className={`${recClass} border-2 p-8 rounded-lg`} data-testid="recommendation-card">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <RecIcon className={`w-12 h-12 ${recColor}`} />
              <div>
                <div className={`text-sm font-medium ${recColor} uppercase tracking-wide mb-1`}>
                  Recommendation
                </div>
                <div className={`text-4xl font-bold ${recColor}`}>
                  {recommendation}
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-slate-400 mb-1">Target Price</div>
              <div className="text-3xl font-bold font-mono text-white">
                ₹{valuation.target_price?.toFixed(0) || valuation.fair_value?.toFixed(0) || 0}
              </div>
              <div className={`text-sm mt-1 font-medium ${
                (valuation.upside_percent || 0) > 0 ? 'text-green-400' : 
                (valuation.upside_percent || 0) < 0 ? 'text-red-400' : 'text-slate-400'
              }`}>
                {(valuation.upside_percent || 0) > 0 ? '↑' : (valuation.upside_percent || 0) < 0 ? '↓' : ''} {Math.abs(valuation.upside_percent || 0).toFixed(1)}% Upside
              </div>
            </div>
          </div>
          
          {/* Market Price Row */}
          <div className="mt-6 pt-6 border-t border-white/10 flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-400 mb-1">Current Market Price</div>
              <div className="text-2xl font-bold font-mono text-white">
                ₹{(valuation.current_price || metadata.current_price || 0).toFixed(2)}
              </div>
            </div>
            <div className="text-right">
              <p className="text-slate-300 max-w-md">
                {thesis.summary || `${recommendation} with target price of ₹${valuation.target_price?.toFixed(0) || valuation.fair_value?.toFixed(0) || 0}`}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="max-w-7xl mx-auto">
        <Tabs defaultValue="thesis" className="w-full">
          <TabsList className="grid w-full grid-cols-2 md:grid-cols-4 bg-slate-900 p-1 rounded-lg mb-6">
            <TabsTrigger 
              value="thesis" 
              className="data-[state=active]:bg-indigo-600 rounded-md transition-colors"
              data-testid="tab-thesis"
            >
              <ScrollText className="w-4 h-4 mr-2" />
              Thesis
            </TabsTrigger>
            <TabsTrigger 
              value="assumptions" 
              className="data-[state=active]:bg-indigo-600 rounded-md transition-colors"
              data-testid="tab-assumptions"
            >
              <SlidersHorizontal className="w-4 h-4 mr-2" />
              Assumptions
            </TabsTrigger>
            <TabsTrigger 
              value="valuation" 
              className="data-[state=active]:bg-indigo-600 rounded-md transition-colors"
              data-testid="tab-valuation"
            >
              <TrendingUp className="w-4 h-4 mr-2" />
              Valuation
            </TabsTrigger>
            <TabsTrigger 
              value="model" 
              className="data-[state=active]:bg-indigo-600 rounded-md transition-colors"
              data-testid="tab-model"
            >
              <Grid3X3 className="w-4 h-4 mr-2" />
              Model
            </TabsTrigger>
          </TabsList>

          <TabsContent value="thesis">
            <div className="glass-card p-8 rounded-lg">
              <h2 className="text-2xl font-bold text-white mb-6">Investment Thesis</h2>
              <div className="prose prose-invert prose-slate max-w-none">
                <pre className="whitespace-pre-wrap font-sans text-slate-300 leading-relaxed">
                  {thesis.full_text || "Thesis is being generated..."}
                </pre>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="assumptions">
            <div className="glass-card p-8 rounded-lg">
              <h2 className="text-2xl font-bold text-white mb-6">Key Assumptions</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700">
                      <th className="text-left py-3 text-slate-400 font-medium">Parameter</th>
                      <th className="text-right py-3 text-slate-400 font-medium">FY26E</th>
                      <th className="text-right py-3 text-slate-400 font-medium">FY27E</th>
                      <th className="text-right py-3 text-slate-400 font-medium">FY28E</th>
                    </tr>
                  </thead>
                  <tbody className="font-mono">
                    <tr className="border-b border-slate-800">
                      <td className="py-3 text-slate-300">Loan Growth (%)</td>
                      <td className="text-right text-white">15.0</td>
                      <td className="text-right text-white">14.5</td>
                      <td className="text-right text-white">14.0</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 text-slate-300">NIM (%)</td>
                      <td className="text-right text-white">3.8</td>
                      <td className="text-right text-white">3.9</td>
                      <td className="text-right text-white">4.0</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 text-slate-300">CASA Ratio (%)</td>
                      <td className="text-right text-white">42.0</td>
                      <td className="text-right text-white">43.0</td>
                      <td className="text-right text-white">44.0</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 text-slate-300">Credit Cost (%)</td>
                      <td className="text-right text-white">0.8</td>
                      <td className="text-right text-white">0.7</td>
                      <td className="text-right text-white">0.6</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-slate-500 mt-6">
                * Download Excel model for complete assumptions and rationale
              </p>
            </div>
          </TabsContent>

          <TabsContent value="valuation">
            <div className="glass-card p-8 rounded-lg">
              <h2 className="text-2xl font-bold text-white mb-6">Valuation Summary</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                {/* Current Price Card */}
                <div className="border border-slate-700 rounded-lg p-6 text-center">
                  <div className="text-sm text-slate-400 mb-2">Current Market Price</div>
                  <div className="text-3xl font-bold font-mono text-white">
                    ₹{(valuation.current_price || metadata.current_price || 0).toFixed(2)}
                  </div>
                </div>
                
                {/* Target Price Card */}
                <div className="border border-indigo-600 rounded-lg p-6 text-center bg-indigo-600/10">
                  <div className="text-sm text-indigo-300 mb-2">Target Price</div>
                  <div className="text-3xl font-bold font-mono text-indigo-400">
                    ₹{(valuation.target_price || valuation.fair_value || 0).toFixed(0)}
                  </div>
                </div>
                
                {/* Upside Card */}
                <div className={`border rounded-lg p-6 text-center ${
                  (valuation.upside_percent || 0) > 0 
                    ? 'border-green-600 bg-green-600/10' 
                    : (valuation.upside_percent || 0) < 0 
                    ? 'border-red-600 bg-red-600/10' 
                    : 'border-slate-700'
                }`}>
                  <div className="text-sm text-slate-400 mb-2">Upside / Downside</div>
                  <div className={`text-3xl font-bold font-mono ${
                    (valuation.upside_percent || 0) > 0 
                      ? 'text-green-400' 
                      : (valuation.upside_percent || 0) < 0 
                      ? 'text-red-400' 
                      : 'text-white'
                  }`}>
                    {(valuation.upside_percent || 0) > 0 ? '+' : ''}{(valuation.upside_percent || 0).toFixed(1)}%
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="border border-slate-700 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">Residual Income Valuation</h3>
                  <div className="space-y-3 font-mono">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Cost of Equity</span>
                      <span className="text-white">{valuation.cost_of_equity || 13.0}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Terminal Growth</span>
                      <span className="text-white">{valuation.terminal_growth || 3.0}%</span>
                    </div>
                    <div className="flex justify-between border-t border-slate-700 pt-3 mt-3">
                      <span className="text-white font-semibold">Fair Value</span>
                      <span className="text-indigo-400 font-semibold">₹{(valuation.fair_value || valuation.target_price || 0).toFixed(0)}</span>
                    </div>
                  </div>
                </div>
                
                <div className="border border-slate-700 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">Valuation Rationale</h3>
                  <p className="text-sm text-slate-400 leading-relaxed">
                    {valuation.rationale || 
                      "Residual Income Valuation (RIV) is the primary methodology for banks as they cannot produce free cash flow in the traditional sense. The model values the bank based on excess returns (ROE above cost of equity) over forecast period."}
                  </p>
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="model">
            <div className="glass-card p-8 rounded-lg">
              <h2 className="text-2xl font-bold text-white mb-6">Model Preview</h2>
              <p className="text-slate-400 mb-6">
                The complete financial model includes 16 sheets with linked formulas. Download the Excel file to view the full model.
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700">
                      <th className="text-left py-3 text-slate-400 font-medium">Sheet</th>
                      <th className="text-left py-3 text-slate-400 font-medium">Description</th>
                    </tr>
                  </thead>
                  <tbody className="text-slate-300">
                    <tr className="border-b border-slate-800">
                      <td className="py-3 font-mono">Cover</td>
                      <td>Summary & Recommendation</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 font-mono">P&L</td>
                      <td>Profit & Loss Statement (FY21-FY30)</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 font-mono">Balance Sheet</td>
                      <td>Assets & Liabilities (FY21-FY30)</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 font-mono">Assumptions</td>
                      <td>Forecast Drivers & Rationale</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 font-mono">Valuation</td>
                      <td>RIV, Peer Comps, DDM</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 font-mono">Thesis</td>
                      <td>Investment Note & Analysis</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* AI Reasoning Panel - Collapsible */}
      {result?.reasoning && (
        <div className="max-w-7xl mx-auto mt-8">
          <button
            onClick={() => setShowReasoning(!showReasoning)}
            className="w-full glass-card p-4 rounded-lg flex items-center justify-between hover:bg-slate-800/50 transition-colors"
            data-testid="reasoning-toggle"
          >
            <div className="flex items-center gap-3">
              <Brain className="w-5 h-5 text-purple-400" />
              <span className="text-white font-medium">AI Reasoning & Analysis</span>
              <span className="text-xs text-slate-500 px-2 py-1 bg-slate-800 rounded">
                {result.tool_calls?.length || 0} tool calls
              </span>
            </div>
            {showReasoning ? (
              <ChevronUp className="w-5 h-5 text-slate-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-slate-400" />
            )}
          </button>
          
          {showReasoning && (
            <div className="glass-card mt-2 p-6 rounded-lg" data-testid="reasoning-panel">
              <h3 className="text-lg font-semibold text-white mb-4">Agent Reasoning</h3>
              <div className="prose prose-invert prose-sm max-w-none">
                <pre className="whitespace-pre-wrap text-sm text-slate-300 bg-slate-900 p-4 rounded-lg overflow-x-auto font-mono leading-relaxed">
                  {result.reasoning}
                </pre>
              </div>
              
              {result.tool_calls && result.tool_calls.length > 0 && (
                <div className="mt-6">
                  <h4 className="text-md font-semibold text-white mb-3">Tool Calls Log</h4>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {result.tool_calls.map((call, idx) => (
                      <div 
                        key={idx} 
                        className={`text-xs p-2 rounded ${
                          call.result_success ? 'bg-green-900/20 border border-green-800' : 'bg-red-900/20 border border-red-800'
                        }`}
                      >
                        <span className="text-slate-400">#{idx + 1}</span>
                        <span className="ml-2 text-white font-mono">{call.tool}</span>
                        <span className={`ml-2 ${call.result_success ? 'text-green-400' : 'text-red-400'}`}>
                          {call.result_success ? '✓' : '✗'}
                        </span>
                        <span className="ml-2 text-slate-500">{call.duration_seconds}s</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="max-w-7xl mx-auto mt-8 text-center">
        <p className="text-xs text-slate-500">
          This model is generated using public data and AI reasoning. It is not investment advice. Verify all assumptions before use.
        </p>
      </div>
    </div>
  );
}
