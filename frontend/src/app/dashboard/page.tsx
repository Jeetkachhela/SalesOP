"use client";

import { useAuth } from "@/store/useAuth";
import { useRouter } from "next/navigation";
import React, { useEffect, useState } from "react";
import UploadInterface from "@/components/UploadInterface";
import SessionControl from "@/components/SessionControl";
import TrustScoreGauge from "@/components/TrustScoreGauge";
import CorrelationHeatmap from "@/components/CorrelationHeatmap";
import DistributionChart from "@/components/DistributionChart";
import TrendLineChart from "@/components/TrendLineChart";
import NLExplorer from "@/components/NLExplorer";
import { fetchApi } from "@/lib/api";
import { 
  Activity, 
  LogOut, 
  Shield, 
  Database, 
  MessagesSquare, 
  Settings2, 
  Send,
  LineChart as ChartIcon, 
  Sparkles,
  Lock,
  Loader2,
  AlertTriangle,
  CheckCircle,
  FileSpreadsheet,
  Clock,
  RefreshCw,
  Trash2
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface DatasetUpload {
  id: string;
  filename: string;
  file_size_bytes: number;
  mime_type: string;
  status: string;
  error_message: string | null;
  created_at: string;
}

export default function Dashboard() {
  const { token, logout, sessionId, generateNewSession } = useAuth();
  const router = useRouter();

  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    if (!sessionId) {
      generateNewSession();
    }
  }, [sessionId, generateNewSession]);

  // Navigation & Datasets list
  const [activeTab, setActiveTab] = useState<"upload" | "analytics" | "explorer" | "intelligence">("upload");
  const [uploads, setUploads] = useState<DatasetUpload[]>([]);
  const [selectedUploadId, setSelectedUploadId] = useState<string | null>(null);
  const [isRegenerating, setIsRegenerating] = useState(false);

  const handleRegenerate = async (uploadId: string) => {
    setIsRegenerating(true);
    const toastId = toast.loading("Re-triggering background analysis...");
    try {
      await fetchApi(`/uploads/${uploadId}/regenerate`, {
        method: "POST"
      });
      toast.success("Analysis regenerated successfully! Processing started.", { id: toastId });
      loadUploads();
    } catch (err: any) {
      toast.error(err.message || "Failed to regenerate analysis.", { id: toastId });
    } finally {
      setIsRegenerating(false);
    }
  };

  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteUpload = async (uploadId: string, event?: React.MouseEvent) => {
    if (event) {
      event.stopPropagation();
    }
    
    const confirmDelete = window.confirm("Are you sure you want to permanently delete this dataset and all of its associated reports?");
    if (!confirmDelete) return;

    setIsDeleting(true);
    const toastId = toast.loading("Deleting dataset...");
    try {
      await fetchApi(`/uploads/${uploadId}`, {
        method: "DELETE"
      });
      toast.success("Dataset deleted successfully.", { id: toastId });
      
      if (selectedUploadId === uploadId) {
        setSelectedUploadId(null);
      }
      
      loadUploads();
    } catch (err: any) {
      toast.error(err.message || "Failed to delete dataset.", { id: toastId });
    } finally {
      setIsDeleting(false);
    }
  };

  // Track which upload ID has already had its analytics fetched — prevents
  // the 5-second polling interval from triggering repeated heavy API calls.
  const analyticsLoadedForId = React.useRef<string | null>(null);
  
  // Analytics Data State
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [trustScore, setTrustScore] = useState<any>(null);
  const [correlations, setCorrelations] = useState<any>(null);
  const [distributions, setDistributions] = useState<any>(null);
  const [trends, setTrends] = useState<any>(null);
  const [aiSummary, setAiSummary] = useState<any>(null);

  // Chat feed state (Wired dynamically later if needed, has simple simulation for now)
  const [chatMessage, setChatMessage] = useState("");
  const [chatLog, setChatLog] = useState<{ role: string; content: string }[]>([
    { role: "assistant", content: "I am ready to help you analyze your data. Select an active dataset to get started." }
  ]);

  // Authenticate user
  useEffect(() => {
    if (isMounted && !token) {
      router.push("/login");
    }
  }, [isMounted, token, router]);

  // Load uploads from API
  const loadUploads = async () => {
    try {
      const data = await fetchApi("/uploads/");
      setUploads(data);
      
      // Auto-select the first upload if nothing is selected yet
      if (data.length > 0 && !selectedUploadId) {
        setSelectedUploadId(data[0].id);
      }
    } catch (err: any) {
      console.error("Error loading uploads:", err);
    }
  };

  // Poll datasets list continuously to check for background parser completion
  useEffect(() => {
    if (!token) return;
    loadUploads();
    
    const interval = setInterval(() => {
      loadUploads();
    }, 5000);
    
    return () => clearInterval(interval);
  }, [token]);

  // Load analytics when selected dataset changes or first becomes ready.
  // We intentionally exclude `uploads` from deps and instead watch a derived
  // status string so the 5-second polling interval never re-triggers a fetch.
  const selectedStatus = uploads.find((u) => u.id === selectedUploadId)?.status ?? null;

  useEffect(() => {
    if (!selectedUploadId) {
      analyticsLoadedForId.current = null;
      clearAnalytics();
      return;
    }

    if (selectedStatus === "VISUALIZATION_READY") {
      // Only fetch if we haven't already loaded data for this exact upload ID
      if (analyticsLoadedForId.current !== selectedUploadId) {
        analyticsLoadedForId.current = selectedUploadId;
        fetchDatasetAnalytics(selectedUploadId);
      }
    } else {
      // Dataset changed to a non-ready one — clear stale data
      if (analyticsLoadedForId.current !== null) {
        analyticsLoadedForId.current = null;
        clearAnalytics();
      }
    }
  }, [selectedUploadId, selectedStatus]);

  const clearAnalytics = React.useCallback(() => {
    setTrustScore(null);
    setCorrelations(null);
    setDistributions(null);
    setTrends(null);
    setAiSummary(null);
  }, []);

  const fetchDatasetAnalytics = React.useCallback(async (uploadId: string) => {
    setLoadingAnalytics(true);
    try {
      const [score, corr, dist, tr, sum] = await Promise.all([
        fetchApi(`/analytics/${uploadId}/trust-score`),
        fetchApi(`/analytics/${uploadId}/correlations`),
        fetchApi(`/analytics/${uploadId}/distributions`),
        fetchApi(`/analytics/${uploadId}/trends`),
        fetchApi(`/analytics/${uploadId}/summary`)
      ]);
      setTrustScore(score);
      setCorrelations(corr);
      setDistributions(dist);
      setTrends(tr);
      setAiSummary(sum);
    } catch (err: any) {
      // Reset the ref so retry is possible after an error
      analyticsLoadedForId.current = null;
      console.error("Failed to load analytics:", err);
      toast.error("Failed to load full analytics report.");
    } finally {
      setLoadingAnalytics(false);
    }
  }, []);



  if (!isMounted) return null;
  if (!token) return null;

  const activeUpload = uploads.find((u) => u.id === selectedUploadId);
  const isReady = activeUpload?.status === "VISUALIZATION_READY";

  const handleChat = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatMessage.trim()) return;

    setChatLog([...chatLog, { role: "user", content: chatMessage }]);
    setChatMessage("");

    // Simple robust conversational support
    setTimeout(() => {
      if (isReady && aiSummary) {
        setChatLog((prev) => [
          ...prev,
          { 
            role: "assistant", 
            content: `Based on the active analysis, this dataset has a Data Trust Score of ${trustScore?.score || "N/A"}% and is categorized as ${trustScore?.score >= 71 ? "Excellent" : "Warning"}. Under the statistical trends, moving averages indicate a ${trends?.metrics?.[Object.keys(trends?.metrics)[0]]?.direction || "stable"} slope.`
          }
        ]);
      } else {
        setChatLog((prev) => [
          ...prev,
          { role: "assistant", content: "I am ready to interpret. Please make sure a successfully analyzed dataset is selected." }
        ]);
      }
    }, 1000);
  };


  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30">
      <SessionControl />
      {/* Decorative Blur Backdrops */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] rounded-full bg-violet-600/10 blur-3xl pointer-events-none -z-10" />
      <div className="absolute top-1/3 right-1/4 w-[600px] h-[600px] rounded-full bg-cyan-600/10 blur-3xl pointer-events-none -z-10" />

      {/* Zero Trust Header */}
      <header className="sticky top-0 z-40 w-full bg-slate-900/80 backdrop-blur-md border-b border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity className="w-6 h-6 text-cyan-400 animate-pulse" />
            <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              SalesOP Operational Intelligence
            </h1>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-xs text-cyan-400 bg-cyan-950/40 border border-cyan-800/30 px-3 py-1.5 rounded-full font-semibold shadow-inner">
              <Shield className="w-3.5 h-3.5" />
              Zero Trust Sandbox
            </div>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={logout}
              className="text-slate-400 hover:text-white hover:bg-slate-800/50 rounded-lg text-xs"
            >
              <LogOut className="w-3.5 h-3.5 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex-1 max-w-7xl w-full mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Side: Upload Panel + Datasets List */}
        <aside className="lg:col-span-4 space-y-6">
          <UploadInterface onUploadSuccess={loadUploads} />

          {/* Datasets list */}
          <div className="border border-slate-800 bg-slate-900/40 backdrop-blur-xl rounded-xl p-4 shadow-xl space-y-3">
            <h3 className="text-xs uppercase font-extrabold text-slate-500 tracking-wider flex items-center gap-2">
              <Database size={14} className="text-cyan-400" />
              Your Datasets
            </h3>

            {uploads.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500 italic border border-slate-800/50 rounded-lg">
                No datasets uploaded yet. Upload a CSV above to begin.
              </div>
            ) : (
              <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1 scrollbar-thin">
                {uploads.map((up) => {
                  const isSelected = up.id === selectedUploadId;
                  const sizeMB = (up.file_size_bytes / 1024 / 1024).toFixed(2);
                  const isProcessing = up.status !== "VISUALIZATION_READY" && up.status !== "FAILED";
                  
                  return (
                    <div
                      key={up.id}
                      onClick={() => setSelectedUploadId(up.id)}
                      className={`p-3 rounded-lg border text-left cursor-pointer transition-all select-none ${
                        isSelected
                          ? "border-cyan-500/80 bg-cyan-950/15 shadow-[0_0_15px_rgba(6,182,212,0.15)]"
                          : "border-slate-800 hover:border-slate-700 bg-slate-950/40"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className={`text-xs font-semibold truncate ${isSelected ? "text-cyan-400" : "text-slate-200"}`}>
                          {up.filename}
                        </p>
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          {isProcessing ? (
                            <Loader2 size={12} className="animate-spin text-cyan-400" />
                          ) : up.status === "VISUALIZATION_READY" ? (
                            <CheckCircle size={12} className="text-emerald-400" />
                          ) : (
                            <AlertTriangle size={12} className="text-rose-400" />
                          )}
                          <button
                            onClick={(e) => handleDeleteUpload(up.id, e)}
                            disabled={isDeleting}
                            title="Delete Dataset"
                            className="text-slate-500 hover:text-rose-400 transition-colors p-0.5 focus:outline-none"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>

                      <div className="flex items-center justify-between text-[10px] text-slate-500 mt-2 font-mono">
                        <span className="flex items-center gap-1">
                          <FileSpreadsheet size={10} />
                          {sizeMB} MB
                        </span>
                        <span className="flex items-center gap-1 capitalize">
                          {isProcessing ? (
                            <span className="text-cyan-400/90 animate-pulse flex items-center gap-1">
                              <Clock size={10} /> {up.status.toLowerCase().replace("_", " ")}
                            </span>
                          ) : up.status === "VISUALIZATION_READY" ? (
                            <span className="text-emerald-500/90">ready</span>
                          ) : (
                            <span className="text-rose-500/90">failed</span>
                          )}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </aside>

        {/* Right Side: Main Tabs content area */}
        <main className="lg:col-span-8 space-y-6 flex flex-col">
          {/* Navigation tabs */}
          <div className="flex border-b border-slate-850 gap-6">
            <button
              onClick={() => setActiveTab("upload")}
              className={`pb-3 font-semibold text-xs tracking-wider uppercase transition-all flex items-center gap-2 border-b-2 outline-none cursor-pointer ${
                activeTab === "upload"
                  ? "border-cyan-500 text-white"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Database className="w-3.5 h-3.5" /> Workspace
            </button>
            
            {/* Analytics - locked if not ready */}
            <button
              onClick={() => isReady && setActiveTab("analytics")}
              disabled={!isReady}
              className={`pb-3 font-semibold text-xs tracking-wider uppercase transition-all flex items-center gap-2 border-b-2 outline-none cursor-default disabled:opacity-40 disabled:cursor-not-allowed ${
                activeTab === "analytics"
                  ? "border-cyan-500 text-white"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              {isReady ? <ChartIcon className="w-3.5 h-3.5 text-cyan-400" /> : <Lock className="w-3 h-3 text-slate-500" />}
              Analytics
            </button>

            {/* Explorer - locked if not ready */}
            <button
              onClick={() => isReady && setActiveTab("explorer")}
              disabled={!isReady}
              className={`pb-3 font-semibold text-xs tracking-wider uppercase transition-all flex items-center gap-2 border-b-2 outline-none cursor-default disabled:opacity-40 disabled:cursor-not-allowed ${
                activeTab === "explorer"
                  ? "border-cyan-500 text-white"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              {isReady ? <Sparkles className="w-3.5 h-3.5 text-violet-400" /> : <Lock className="w-3 h-3 text-slate-500" />}
              NL Explorer
            </button>

            {/* Intelligence - locked if not ready */}
            <button
              onClick={() => isReady && setActiveTab("intelligence")}
              disabled={!isReady}
              className={`pb-3 font-semibold text-xs tracking-wider uppercase transition-all flex items-center gap-2 border-b-2 outline-none cursor-default disabled:opacity-40 disabled:cursor-not-allowed ${
                activeTab === "intelligence"
                  ? "border-cyan-500 text-white"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              {isReady ? <MessagesSquare className="w-3.5 h-3.5 text-cyan-400" /> : <Lock className="w-3 h-3 text-slate-500" />}
              Intelligence Feed
            </button>
          </div>

          {/* Active Tab rendering */}
          <div className="flex-1">
            
            {/* 1. Upload/Workspace Tab */}
            {activeTab === "upload" && (
              <div className="space-y-6">
                {activeUpload ? (
                  <div className="border border-slate-800 bg-slate-900/40 backdrop-blur-xl rounded-xl p-6 shadow-xl space-y-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <h2 className="text-xl font-bold text-white flex items-center gap-2">
                          {activeUpload.filename}
                        </h2>
                        <p className="text-xs text-slate-500 font-mono mt-1 flex items-center gap-3 flex-wrap">
                          <span>UUID: {activeUpload.id}</span>
                          <span className="text-slate-800">|</span>
                          <button 
                            onClick={() => handleRegenerate(activeUpload.id)}
                            disabled={isRegenerating}
                            title="Regenerate all statistics and AI insights for this dataset"
                            className="text-slate-400 hover:text-cyan-400 disabled:opacity-50 transition-colors flex items-center gap-1.5 focus:outline-none"
                          >
                            <RefreshCw className={`w-3.5 h-3.5 ${isRegenerating ? 'animate-spin' : ''}`} />
                            <span className="text-[10px] font-sans font-bold hover:underline">Regenerate Analysis</span>
                          </button>
                          <span className="text-slate-800">|</span>
                          <button 
                            onClick={(e) => handleDeleteUpload(activeUpload.id, e)}
                            disabled={isDeleting}
                            title="Delete dataset and reports permanently"
                            className="text-slate-400 hover:text-rose-400 disabled:opacity-50 transition-colors flex items-center gap-1.5 focus:outline-none"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            <span className="text-[10px] font-sans font-bold hover:underline">Delete Dataset</span>
                          </button>
                        </p>
                      </div>
                      <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold border ${
                        isReady 
                          ? "text-emerald-400 border-emerald-500/20 bg-emerald-500/5" 
                          : activeUpload.status === "FAILED"
                          ? "text-rose-400 border-rose-500/20 bg-rose-500/5 animate-pulse"
                          : "text-cyan-400 border-cyan-500/20 bg-cyan-500/5 animate-pulse"
                      }`}>
                        {activeUpload.status.replace("_", " ")}
                      </span>
                    </div>

                    {!isReady && activeUpload.status !== "FAILED" && (
                      <div className="p-4 bg-slate-950/40 border border-slate-850 rounded-xl space-y-3 text-center">
                        <Loader2 className="w-8 h-8 text-cyan-400 animate-spin mx-auto" />
                        <h4 className="text-sm font-semibold text-slate-200">Executing Deterministic Analytics...</h4>
                        <p className="text-xs text-slate-500 max-w-sm mx-auto">
                          Our background pipeline is currently parsing your CSV data, executing schema intelligence checks, and conducting statistical anomaly tests. Visualizations will mount automatically.
                        </p>
                      </div>
                    )}

                    {activeUpload.status === "FAILED" && (
                      <div className="p-4 bg-rose-950/10 border border-rose-900/20 rounded-xl space-y-3 text-center text-xs">
                        <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto" />
                        <h4 className="font-semibold text-rose-400">Processing Pipeline Failed</h4>
                        <p className="text-slate-400 max-w-xs mx-auto">
                          Error Details: {activeUpload.error_message || "Unknown error during CSV parsing."}
                        </p>
                        <Button 
                          size="sm" 
                          variant="outline" 
                          onClick={() => handleRegenerate(activeUpload.id)}
                          disabled={isRegenerating}
                          className="mt-2 border-rose-500/30 hover:bg-rose-500/10 hover:text-rose-400 text-rose-300 gap-1.5 mx-auto flex items-center"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${isRegenerating ? 'animate-spin' : ''}`} />
                          Regenerate Analysis
                        </Button>
                      </div>
                    )}

                    {isReady && (
                      <div className="space-y-4">
                        <div className="p-4 bg-slate-950/40 border border-slate-850 rounded-xl grid grid-cols-2 gap-4 text-center">
                          <div>
                            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Analysis Status</p>
                            <p className="text-xs font-bold text-emerald-400 mt-1 flex items-center justify-center gap-1">
                              <CheckCircle size={12} /> Complete
                            </p>
                          </div>
                          <div>
                            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Visualizations</p>
                            <p className="text-xs font-bold text-slate-300 mt-1">
                              Unlocked / Active
                            </p>
                          </div>
                        </div>
                        
                        <div className="p-4 border border-slate-800 rounded-xl bg-slate-950/20 text-xs text-slate-400 space-y-2">
                          <p className="font-semibold text-slate-300">Quick Guide:</p>
                          <ul className="list-disc pl-4 space-y-1">
                            <li>Go to the <strong className="text-cyan-400">Analytics</strong> tab to view the animated Data Trust Score™ gauge, the correlation heatmap, frequency distributions, and resampled moving averages.</li>
                            <li>Go to the <strong className="text-violet-400">NL Explorer</strong> tab to ask natural language questions in English and see the AI formulate dynamic charts on-the-fly.</li>
                            <li>Go to the <strong className="text-cyan-400">Intelligence Feed</strong> tab to browse flagged outlier anomalies and chat about operational takeaways.</li>
                          </ul>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="border border-slate-800 bg-slate-900/40 backdrop-blur-xl rounded-xl p-8 shadow-xl text-center flex flex-col items-center justify-center h-72">
                    <Database className="w-12 h-12 text-slate-700 mb-4" />
                    <h3 className="text-md font-bold text-slate-300">No Dataset Selected</h3>
                    <p className="text-xs text-slate-500 max-w-xs mt-1">
                      Upload a dataset on the left or select an existing one to unlock advanced analytics.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* 3. Analytics Tab */}
            {activeTab === "analytics" && (
              <div className="space-y-6">
                {loadingAnalytics ? (
                  <div className="py-20 text-center space-y-3">
                    <Loader2 size={36} className="animate-spin text-cyan-400 mx-auto" />
                    <p className="text-xs text-slate-500 font-mono">Loading full visual reports from database...</p>
                  </div>
                ) : isReady && trustScore ? (
                  <div className="space-y-6 animate-fade-in duration-500">
                    
                    {/* Gauge and AI Summary side-by-side */}
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-stretch">
                      <div className="md:col-span-5 flex">
                        <div className="w-full">
                          <TrustScoreGauge score={trustScore.score} breakdown={trustScore.breakdown} />
                        </div>
                      </div>
                      <div className="md:col-span-7 flex">
                        <Card className="border-slate-800 bg-slate-900/50 backdrop-blur-xl shadow-2xl relative overflow-hidden p-6 flex flex-col justify-between w-full">
                          <div className="absolute top-0 right-0 w-48 h-48 bg-violet-600/5 blur-3xl" />
                          <div className="space-y-3">
                            <h4 className="text-xs uppercase font-extrabold text-slate-500 tracking-wider flex items-center gap-1.5">
                              <Sparkles size={14} className="text-violet-400 animate-pulse" />
                              Operational Summary (AI Interpretation)
                            </h4>
                            <p className="text-sm font-semibold text-slate-200 leading-relaxed">
                              {aiSummary?.summary}
                            </p>
                            
                            {/* Bullet points insights */}
                            {aiSummary?.interpretation?.insights && (
                              <ul className="space-y-2 mt-4">
                                {aiSummary.interpretation.insights.slice(0, 3).map((ins: string, idx: number) => (
                                  <li key={idx} className="text-xs text-slate-400 flex items-start gap-2 leading-relaxed">
                                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-1.5 flex-shrink-0" />
                                    <span>{ins}</span>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                          
                          <div className="border-t border-slate-850 pt-4 mt-6 flex justify-between items-center text-[10px] text-slate-500 font-mono">
                            <span>Engine: Groq LLaMA3.1-8B-Instant</span>
                            <span>Temp: 0.1 (Strict Objectivity)</span>
                          </div>
                        </Card>
                      </div>
                    </div>

                    {/* Correlation Heatmap */}
                    {correlations && (
                      <CorrelationHeatmap 
                        matrix={correlations.matrix} 
                        strongCorrelations={correlations.strong_correlations} 
                      />
                    )}

                    {/* Distribution Bins & Trend Lines side by side */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      {distributions && <DistributionChart distributions={distributions} />}
                      {trends && <TrendLineChart trends={trends} />}
                    </div>

                  </div>
                ) : (
                  <div className="py-12 text-center text-xs text-slate-500 italic">
                    Select a ready dataset to load analytics.
                  </div>
                )}
              </div>
            )}

            {/* 4. NL Explorer Tab */}
            {activeTab === "explorer" && selectedUploadId && isReady && (
              <div className="animate-fade-in duration-500">
                <NLExplorer uploadId={selectedUploadId} />
              </div>
            )}

            {/* 5. Intelligence / Anomaly Feed Tab */}
            {activeTab === "intelligence" && isReady && (
              <div className="grid grid-cols-1 md:grid-cols-12 gap-6 h-[600px] animate-fade-in duration-500">
                {/* Anomaly Feed Panel */}
                <div className="md:col-span-8 border border-slate-800 bg-slate-900/40 backdrop-blur-xl overflow-y-auto p-6 rounded-xl flex flex-col shadow-xl">
                  <h3 className="font-bold text-lg text-white mb-4 border-b border-slate-800 pb-2">Anomaly Feed</h3>
                  <div className="space-y-4 flex-1 overflow-y-auto pr-1">
                    
                    {aiSummary?.interpretation?.anomalies_highlighted && aiSummary.interpretation.anomalies_highlighted.length > 0 ? (
                      aiSummary.interpretation.anomalies_highlighted.map((anom: string, idx: number) => (
                        <div key={idx} className="p-4 border border-rose-500/20 bg-rose-500/5 rounded-lg flex gap-3">
                          <AlertTriangle className="text-rose-400 mt-0.5 flex-shrink-0" size={16} />
                          <div>
                            <span className="font-semibold text-xs text-rose-400">Statistical Alert</span>
                            <p className="text-xs text-slate-200 mt-1">{anom}</p>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="p-4 border border-emerald-500/20 bg-emerald-500/5 rounded-lg flex gap-3">
                        <CheckCircle className="text-emerald-400 mt-0.5 flex-shrink-0" size={16} />
                        <div>
                          <span className="font-semibold text-xs text-emerald-400">Statistical Health Stable</span>
                          <p className="text-xs text-slate-200 mt-1">No significant anomalies were flagged in the numerical fields of this dataset.</p>
                        </div>
                      </div>
                    )}

                    {aiSummary?.interpretation?.data_quality_warnings && aiSummary.interpretation.data_quality_warnings.map((warn: string, idx: number) => (
                      <div key={idx} className="p-4 border border-amber-500/20 bg-amber-500/5 rounded-lg flex gap-3">
                        <AlertTriangle className="text-amber-400 mt-0.5 flex-shrink-0" size={16} />
                        <div>
                          <span className="font-semibold text-xs text-amber-400">Quality Warning</span>
                          <p className="text-xs text-slate-200 mt-1">{warn}</p>
                        </div>
                      </div>
                    ))}

                  </div>
                </div>
                
                {/* Chat Panel */}
                <div className="md:col-span-4 border border-slate-800 bg-slate-900/40 backdrop-blur-xl flex flex-col rounded-xl shadow-xl overflow-hidden">
                  <div className="p-4 border-b border-slate-850 bg-slate-950/20 flex items-center gap-2">
                    <MessagesSquare className="w-4 h-4 text-cyan-400"/>
                    <h3 className="font-semibold text-xs uppercase tracking-wider text-slate-300">AI Interpreter</h3>
                  </div>
                  <div className="flex-1 overflow-y-auto p-4 space-y-4 pr-1 scrollbar-thin">
                    {chatLog.map((msg, i) => (
                      <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`p-3 rounded-lg max-w-[85%] text-xs leading-relaxed ${
                          msg.role === 'user' 
                            ? 'bg-cyan-600 text-white font-medium rounded-tr-none' 
                            : 'bg-slate-950 text-slate-200 border border-slate-850 rounded-tl-none'
                        }`}>
                          {msg.content}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="p-3 border-t border-slate-850 bg-slate-950/20">
                    <form onSubmit={handleChat} className="flex gap-2">
                      <input 
                        placeholder="Ask about the anomalies..." 
                        value={chatMessage}
                        onChange={(e) => setChatMessage(e.target.value)}
                        className="flex-1 bg-slate-950 border border-slate-800 focus:border-cyan-500 text-xs rounded-lg px-3 py-2 text-white outline-none"
                      />
                      <Button type="submit" size="icon" className="bg-cyan-600 hover:bg-cyan-500 rounded-lg p-2 flex items-center justify-center">
                        <Send className="w-3.5 h-3.5"/>
                      </Button>
                    </form>
                  </div>
                </div>
              </div>
            )}

          </div>
        </main>

      </div>
    </div>
  );
}
