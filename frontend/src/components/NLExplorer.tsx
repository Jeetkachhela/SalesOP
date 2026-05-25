"use client";

import React, { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { fetchApi } from "@/lib/api";
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend
} from "recharts";
import { Sparkles, Send, Loader2, BarChart2, MessageSquare, AlertCircle } from "lucide-react";
import { toast } from "sonner";

interface NLExplorerProps {
  uploadId: string;
}

interface ChartConfig {
  type: "line" | "bar" | "scatter" | "pie" | "none";
  x_key: string;
  y_keys: string[];
  data: Array<Record<string, any>>;
}

interface ExplorerResponse {
  answer: string;
  chart_config: ChartConfig;
}

export default function NLExplorer({ uploadId }: NLExplorerProps) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ExplorerResponse | null>(null);

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    try {
      const res = await fetchApi(`/analytics/${uploadId}/explore`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      setResult(res);
      toast.success("AI Analysis complete!");
    } catch (err: any) {
      toast.error(err.message || "Failed to query AI explorer.");
    } finally {
      setLoading(false);
    }
  };

  const chartColors = ["#3b82f6", "#06b6d4", "#8b5cf6", "#ec4899", "#f59e0b"];

  const renderDynamicChart = () => {
    if (!result || !result.chart_config || result.chart_config.type === "none") return null;

    const { type, x_key, y_keys, data } = result.chart_config;
    
    if (!data || data.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center p-6 text-slate-500 border border-dashed border-slate-850 rounded-xl bg-slate-950/20 text-xs">
          <AlertCircle size={20} className="mb-1.5" />
          No data was returned for this chart configuration.
        </div>
      );
    }

    return (
      <div className="space-y-3">
        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5 pt-2">
          <BarChart2 size={14} className="text-cyan-400" />
          Interactive Visualization
        </h4>
        <div className="h-64 w-full bg-slate-950/40 border border-slate-850 rounded-xl p-2">
          <ResponsiveContainer width="100%" height="100%">
            {type === "line" ? (
              <LineChart data={data} margin={{ top: 15, right: 15, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey={x_key} stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
                <YAxis stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#020617", borderColor: "#1e293b" }}
                  itemStyle={{ color: "#f8fafc", fontFamily: "monospace" }}
                  labelStyle={{ color: "#94a3b8", fontWeight: "bold" }}
                />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 10 }} />
                {y_keys.map((key, idx) => (
                  <Line
                    key={key}
                    type="monotone"
                    dataKey={key}
                    stroke={chartColors[idx % chartColors.length]}
                    strokeWidth={2}
                    dot={{ r: 2, fill: chartColors[idx % chartColors.length] }}
                    activeDot={{ r: 4 }}
                  />
                ))}
              </LineChart>
            ) : (
              <BarChart data={data} margin={{ top: 15, right: 15, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey={x_key} stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
                <YAxis stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#020617", borderColor: "#1e293b" }}
                  itemStyle={{ color: "#f8fafc", fontFamily: "monospace" }}
                  labelStyle={{ color: "#94a3b8", fontWeight: "bold" }}
                />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 10 }} />
                {y_keys.map((key, idx) => (
                  <Bar
                    key={key}
                    dataKey={key}
                    fill={chartColors[idx % chartColors.length]}
                    radius={[4, 4, 0, 0]}
                  />
                ))}
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>
      </div>
    );
  };

  return (
    <Card className="border-slate-800 bg-slate-900/50 backdrop-blur-xl shadow-2xl relative overflow-hidden transition-all duration-300">
      <div className="absolute top-0 right-0 w-80 h-80 rounded-full bg-violet-500/5 blur-3xl -z-10" />
      
      <CardHeader className="pb-3 border-b border-slate-850">
        <CardTitle className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          <Sparkles size={20} className="text-violet-400 animate-pulse" />
          Natural Language Data Explorer
        </CardTitle>
        <CardDescription className="text-slate-400">
          Query this dataset in plain English to dynamically generate answers and matching Recharts visualizations
        </CardDescription>
      </CardHeader>

      <CardContent className="pt-6 space-y-6">
        {/* Suggestion Prompts */}
        <div className="space-y-1.5">
          <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Suggested Queries</p>
          <div className="flex flex-wrap gap-2">
            {[
              "Are there any strong correlations in the dataset?",
              "What is the distribution of numeric columns?",
              "How have key metrics changed over time?",
              "Show me a summary of missing values or anomalies."
            ].map((suggest, idx) => (
              <button
                key={idx}
                onClick={() => setQuestion(suggest)}
                disabled={loading}
                className="text-xs bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-violet-500/50 px-3 py-1.5 rounded-lg transition-colors cursor-pointer select-none disabled:opacity-50"
              >
                {suggest}
              </button>
            ))}
          </div>
        </div>

        {/* Input Bar Form */}
        <form onSubmit={handleAsk} className="flex gap-2 relative">
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading}
            placeholder="Ask a question about your dataset (e.g., 'What was the highest payment month?')..."
            className="flex-1 bg-slate-950 border-slate-800 focus:border-violet-500 text-white rounded-xl py-5 pl-4 pr-12 focus-visible:ring-0 focus-visible:ring-offset-0"
          />
          <Button
            type="submit"
            disabled={loading || !question.trim()}
            className="absolute right-1 top-1 bottom-1 bg-violet-600 hover:bg-violet-500 text-white rounded-lg flex items-center justify-center p-2.5 min-w-0 transition-colors"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </Button>
        </form>

        {/* AI Answer Bubble */}
        {result && (
          <div className="space-y-4 border-t border-slate-850 pt-5 animate-fade-in duration-500">
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                <MessageSquare size={14} className="text-violet-400" />
                AI Explorer Answer
              </h4>
              <div className="p-4 rounded-xl border border-violet-500/10 bg-violet-500/5 text-sm text-slate-200 leading-relaxed shadow-lg shadow-violet-950/5">
                {result.answer}
              </div>
            </div>

            {/* Dynamic visual */}
            {renderDynamicChart()}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
