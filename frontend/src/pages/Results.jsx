import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { 
  Download, TrendingUp, TrendingDown, Minus, ScrollText, 
  SlidersHorizontal, Grid3X3, Loader2, ChevronDown, ChevronUp,
  BarChart3, ArrowLeft, ExternalLink
} from "lucide-react";
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
      console.error("Download failed:", err);
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-emerald-400 animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Loading results...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-slate-900 border border-slate-800 p-8 rounded-xl text-center">
          <p className="text-red-400 mb-6">{error}</p>
          <button
            onClick={() => navigate("/")}
            className="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-2 rounded-lg transition-colors"
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
  
  // Helper function to convert thesis points to array (handles both string and array formats)
  const parseThesisPoints = (points) => {
    if (!points) return [];
    if (Array.isArray(points)) return points;
    if (typeof points === 'string') {
      // Split by numbered points (e.g., "1. xxx 2. xxx") or newlines
      const parsed = points
        .split(/(?=\d+\.\s)/)
        .map(p => p.replace(/^\d+\.\s*/, '').trim())
        .filter(p => p.length > 0);
      return parsed.length > 0 ? parsed : [points];
    }
    return [];
  };
  
  const bullCase = parseThesisPoints(thesis.bull_case);
  const bearCase = parseThesisPoints(thesis.bear_case);
  const catalysts = parseThesisPoints(thesis.catalysts);
  
  const recommendation = valuation.recommendation || "HOLD";
  const recColor = recommendation === "BUY" ? "text-emerald-400" : 
                   recommendation === "SELL" ? "text-red-400" : 
                   "text-amber-400";
  const recBg = recommendation === "BUY" ? "bg-emerald-500/10 border-emerald-500/30" : 
               recommendation === "SELL" ? "bg-red-500/10 border-red-500/30" : 
               "bg-amber-500/10 border-amber-500/30";
  const RecIcon = recommendation === "BUY" ? TrendingUp : 
                  recommendation === "SELL" ? TrendingDown : 
                  Minus;

  const currentPrice = valuation.current_price || metadata.current_price || 0;
  const targetPrice = valuation.target_price || valuation.fair_value || 0;
  const upside = valuation.upside_percent || (targetPrice && currentPrice ? ((targetPrice - currentPrice) / currentPrice * 100) : 0);

  return (
    <div className="min-h-screen bg-[#0a0e17]">
      {/* Header */}
      <header className="bg-[#0a0e17]/80 backdrop-blur-xl border-b border-slate-800/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate("/")}
                className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-5 h-5 text-slate-400" />
              </button>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-lg flex items-center justify-center">
                  <BarChart3 className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white font-mono">{result.ticker}</h1>
                  <p className="text-sm text-slate-500">{metadata.sector || "Company Analysis"}</p>
                </div>
              </div>
            </div>
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 text-white font-medium rounded-lg transition-colors"
              data-testid="download-excel-button"
            >
              {downloading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )}
              Download Excel
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {/* Recommendation */}
          <div className={`col-span-1 md:col-span-2 p-6 rounded-xl border ${recBg}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400 mb-1">Recommendation</p>
                <div className={`text-4xl font-bold ${recColor} flex items-center gap-3`}>
                  <RecIcon className="w-8 h-8" />
                  {recommendation}
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-slate-400 mb-1">Target Price</p>
                <div className="text-3xl font-bold text-white font-mono">
                  ₹{targetPrice.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </div>
                <div className={`text-sm font-medium ${upside >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {upside >= 0 ? '↑' : '↓'} {Math.abs(upside).toFixed(1)}% Upside
                </div>
              </div>
            </div>
          </div>
          
          {/* Current Price */}
          <div className="p-6 bg-slate-900/50 border border-slate-800/50 rounded-xl">
            <p className="text-sm text-slate-400 mb-1">Current Price</p>
            <div className="text-2xl font-bold text-white font-mono">
              ₹{currentPrice.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
            </div>
          </div>
          
          {/* Market Cap */}
          <div className="p-6 bg-slate-900/50 border border-slate-800/50 rounded-xl">
            <p className="text-sm text-slate-400 mb-1">Market Cap</p>
            <div className="text-2xl font-bold text-white font-mono">
              ₹{((metadata.market_cap || 0) / 100000).toFixed(1)}L Cr
            </div>
          </div>
        </div>

        {/* Thesis Summary */}
        {thesis.summary && (
          <div className="mb-8 p-6 bg-slate-900/30 border border-slate-800/50 rounded-xl">
            <p className="text-slate-300 leading-relaxed">{thesis.summary}</p>
          </div>
        )}

        {/* Tabs */}
        <Tabs defaultValue="thesis" className="w-full">
          <TabsList className="w-full bg-slate-900/50 border border-slate-800/50 rounded-xl p-1 mb-6">
            <TabsTrigger 
              value="thesis" 
              className="flex-1 py-3 data-[state=active]:bg-emerald-600 data-[state=active]:text-white rounded-lg transition-all"
            >
              <ScrollText className="w-4 h-4 mr-2" />
              Thesis
            </TabsTrigger>
            <TabsTrigger 
              value="valuation" 
              className="flex-1 py-3 data-[state=active]:bg-emerald-600 data-[state=active]:text-white rounded-lg transition-all"
            >
              <SlidersHorizontal className="w-4 h-4 mr-2" />
              Valuation
            </TabsTrigger>
            <TabsTrigger 
              value="model" 
              className="flex-1 py-3 data-[state=active]:bg-emerald-600 data-[state=active]:text-white rounded-lg transition-all"
            >
              <Grid3X3 className="w-4 h-4 mr-2" />
              Model Info
            </TabsTrigger>
          </TabsList>

          <TabsContent value="thesis">
            <div className="bg-slate-900/30 border border-slate-800/50 p-8 rounded-xl space-y-8">
              {/* Bull Case */}
              {bullCase.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-emerald-400 mb-4 flex items-center gap-2">
                    <TrendingUp className="w-5 h-5" />
                    Bull Case
                  </h3>
                  <ul className="space-y-2">
                    {bullCase.map((point, i) => (
                      <li key={i} className="flex items-start gap-3 text-slate-300">
                        <span className="text-emerald-500 mt-1">•</span>
                        {point}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {/* Bear Case */}
              {bearCase.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-red-400 mb-4 flex items-center gap-2">
                    <TrendingDown className="w-5 h-5" />
                    Bear Case
                  </h3>
                  <ul className="space-y-2">
                    {bearCase.map((point, i) => (
                      <li key={i} className="flex items-start gap-3 text-slate-300">
                        <span className="text-red-500 mt-1">•</span>
                        {point}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {/* Catalysts */}
              {catalysts.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-amber-400 mb-4">Key Catalysts</h3>
                  <ul className="space-y-2">
                    {catalysts.map((point, i) => (
                      <li key={i} className="flex items-start gap-3 text-slate-300">
                        <span className="text-amber-500 mt-1">•</span>
                        {point}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {/* Fallback */}
              {!thesis.summary && bullCase.length === 0 && bearCase.length === 0 && (
                <p className="text-slate-500 text-center py-8">Thesis details will appear here once analysis is complete.</p>
              )}
            </div>
          </TabsContent>

          <TabsContent value="valuation">
            <div className="bg-slate-900/30 border border-slate-800/50 p-8 rounded-xl">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Valuation Metrics */}
                <div>
                  <h3 className="text-lg font-semibold text-white mb-4">Valuation Metrics</h3>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center py-3 border-b border-slate-800">
                      <span className="text-slate-400">Methodology</span>
                      <span className="text-white font-medium">{valuation.methodology || "Residual Income"}</span>
                    </div>
                    <div className="flex justify-between items-center py-3 border-b border-slate-800">
                      <span className="text-slate-400">Current P/B</span>
                      <span className="text-white font-mono">{valuation.current_pb?.toFixed(2) || "-"}x</span>
                    </div>
                    <div className="flex justify-between items-center py-3 border-b border-slate-800">
                      <span className="text-slate-400">Fair P/B</span>
                      <span className="text-white font-mono">{valuation.fair_pb?.toFixed(2) || "-"}x</span>
                    </div>
                    <div className="flex justify-between items-center py-3 border-b border-slate-800">
                      <span className="text-slate-400">Book Value</span>
                      <span className="text-white font-mono">₹{valuation.book_value?.toFixed(2) || "-"}</span>
                    </div>
                  </div>
                </div>
                
                {/* Key Rationale */}
                <div>
                  <h3 className="text-lg font-semibold text-white mb-4">Valuation Rationale</h3>
                  <p className="text-slate-300 leading-relaxed">
                    {valuation.rationale || "The valuation is based on a Residual Income model appropriate for banking stocks, considering the bank's ROE trajectory, cost of equity, and sustainable growth rates."}
                  </p>
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="model">
            <div className="bg-slate-900/30 border border-slate-800/50 p-8 rounded-xl">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <h3 className="text-lg font-semibold text-white mb-4">Model Contents</h3>
                  <ul className="space-y-2 text-slate-300">
                    <li className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
                      Cover Sheet with recommendation
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
                      P&L Statement (Historical + 5Y Forecast)
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
                      Balance Sheet
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
                      ROE Decomposition Tree
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
                      Quarterly Results
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
                      Key Ratios
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
                      Valuation (RIV/DCF)
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
                      Investment Thesis
                    </li>
                  </ul>
                </div>
                
                <div>
                  <h3 className="text-lg font-semibold text-white mb-4">Data Sources</h3>
                  <ul className="space-y-2 text-slate-300">
                    <li className="flex items-center gap-2">
                      <ExternalLink className="w-4 h-4 text-slate-500" />
                      Screener.in (Financials)
                    </li>
                    <li className="flex items-center gap-2">
                      <ExternalLink className="w-4 h-4 text-slate-500" />
                      Yahoo Finance (Market Data)
                    </li>
                    <li className="flex items-center gap-2">
                      <ExternalLink className="w-4 h-4 text-slate-500" />
                      BSE/NSE (Investor Documents)
                    </li>
                    <li className="flex items-center gap-2">
                      <ExternalLink className="w-4 h-4 text-slate-500" />
                      Claude AI (Analysis)
                    </li>
                  </ul>
                </div>
              </div>
              
              <div className="mt-8 pt-6 border-t border-slate-800">
                <button
                  onClick={handleDownload}
                  disabled={downloading}
                  className="w-full flex items-center justify-center gap-2 py-4 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-xl transition-colors"
                >
                  {downloading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Download className="w-5 h-5" />
                  )}
                  Download Complete Model (.xlsx)
                </button>
              </div>
            </div>
          </TabsContent>
        </Tabs>

        {/* AI Reasoning (Collapsible) */}
        {result.result?.reasoning && (
          <div className="mt-8">
            <button
              onClick={() => setShowReasoning(!showReasoning)}
              className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
            >
              {showReasoning ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              <span className="text-sm">AI Reasoning Log</span>
            </button>
            
            {showReasoning && (
              <div className="mt-4 p-6 bg-slate-900/30 border border-slate-800/50 rounded-xl">
                <pre className="text-sm text-slate-400 whitespace-pre-wrap font-mono leading-relaxed">
                  {result.result.reasoning}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="py-6 px-6 border-t border-slate-800/50 mt-8">
        <div className="max-w-7xl mx-auto text-center text-sm text-slate-600">
          This model is generated using public data and AI reasoning. It is not investment advice. Verify all assumptions before use.
        </div>
      </footer>
    </div>
  );
}
