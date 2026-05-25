"use client";

import React, { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip,
  Legend
} from "recharts";
import { Calendar, TrendingUp, TrendingDown, Minus, AlertCircle, HelpCircle } from "lucide-react";

interface TrendMetric {
  slope: number;
  direction: "upward" | "downward" | "stable";
  moving_average: number[];
}

interface TrendLineChartProps {
  trends: {
    primary_datetime_column: string | null;
    resample_period: "day" | "week" | "month" | null;
    series: Array<Record<string, any>>;
    metrics: Record<string, TrendMetric>;
  };
}

export default function TrendLineChart({ trends }: TrendLineChartProps) {
  const metricsCols = Object.keys(trends.metrics);
  const [selectedMetric, setSelectedMetric] = useState(metricsCols[0] || "");

  if (!trends.primary_datetime_column || trends.series.length === 0 || metricsCols.length === 0 || !selectedMetric) {
    return (
      <Card className="border-slate-800 bg-slate-900/50 backdrop-blur-xl shadow-xl">
        <CardContent className="flex flex-col items-center justify-center p-8 text-center text-slate-400">
          <AlertCircle size={36} className="text-slate-500 mb-3" />
          <p className="font-semibold text-slate-300">Time-Series Trends Unavailable</p>
          <p className="text-xs max-w-xs mt-1">
            No valid date or timestamp columns were detected. Trend and moving average analyses require datetime fields.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Interleave moving average values from metrics into the flat series array
  const currentMetricInfo = trends.metrics[selectedMetric];
  const chartData = trends.series.map((point, idx) => ({
    date: point.date,
    value: point[selectedMetric],
    moving_average: currentMetricInfo?.moving_average?.[idx] ?? null
  }));

  // Define trend direction indicators
  let TrendIcon = Minus;
  let trendColor = "text-slate-400 border-slate-700 bg-slate-800/40";
  let trendLabel = "Stable";
  
  if (currentMetricInfo?.direction === "upward") {
    TrendIcon = TrendingUp;
    trendColor = "text-emerald-400 border-emerald-500/20 bg-emerald-500/10 shadow-[0_0_8px_rgba(16,185,129,0.15)]";
    trendLabel = "Upward Trend";
  } else if (currentMetricInfo?.direction === "downward") {
    TrendIcon = TrendingDown;
    trendColor = "text-rose-400 border-rose-500/20 bg-rose-500/10 shadow-[0_0_8px_rgba(244,63,94,0.15)]";
    trendLabel = "Downward Trend";
  }

  return (
    <Card className="border-slate-800 bg-slate-900/50 backdrop-blur-xl shadow-2xl relative overflow-hidden transition-all duration-300">
      <div className="absolute -top-24 -left-24 w-48 h-48 rounded-full bg-indigo-600/5 blur-3xl" />
      
      <CardHeader className="pb-3 border-b border-slate-850 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <CardTitle className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            Time-Series &amp; Trends
          </CardTitle>
          <CardDescription className="text-slate-400 flex items-center gap-1.5 mt-0.5">
            <Calendar size={14} className="text-indigo-400" />
            Detected date field: <span className="text-slate-200 font-semibold font-mono">{trends.primary_datetime_column}</span> (resampled by {trends.resample_period})
          </CardDescription>
        </div>
        
        {/* Dropdown Selector */}
        <div className="flex items-center gap-2">
          <label htmlFor="trend-select" className="text-xs text-slate-400 font-medium">Plot Metric:</label>
          <select
            id="trend-select"
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(e.target.value)}
            className="text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 px-3 py-2 outline-none focus:border-cyan-500 transition-colors"
          >
            {metricsCols.map((col) => (
              <option key={col} value={col}>
                {col}
              </option>
            ))}
          </select>
        </div>
      </CardHeader>
      
      <CardContent className="pt-6 space-y-6">
        {/* Trend Banner */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 bg-slate-950/40 border border-slate-850 rounded-xl">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg border flex items-center justify-center ${trendColor}`}>
              <TrendIcon size={20} />
            </div>
            <div>
              <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Trend Direction</p>
              <h4 className="text-md font-bold text-slate-200">{trendLabel}</h4>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs">
            <div className="text-right">
              <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Linear Slope</p>
              <p className="font-mono font-semibold text-slate-300 mt-0.5">
                {currentMetricInfo?.slope > 0 ? "+" : ""}{currentMetricInfo?.slope.toFixed(4)}
              </p>
            </div>
            <div className="text-right group relative cursor-pointer text-slate-500 hover:text-slate-400">
              <HelpCircle size={14} />
              <div className="absolute right-0 bottom-full mb-2 w-52 p-2.5 bg-slate-950 border border-slate-800 rounded text-[10px] text-slate-300 shadow-2xl invisible group-hover:visible transition-all duration-200 z-50">
                Slope computed via standard linear regression. Direction is upward if relative slope increases &gt; 1% per period, downward if &lt; -1%, and stable otherwise.
              </div>
            </div>
          </div>
        </div>

        {/* Recharts Line Chart */}
        <div className="h-72 w-full bg-slate-950/20 border border-slate-900 rounded-xl p-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 15, right: 15, left: -20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis 
                dataKey="date" 
                stroke="#64748b" 
                fontSize={10} 
                tickLine={false} 
                axisLine={false}
              />
              <YAxis 
                stroke="#64748b" 
                fontSize={10} 
                tickLine={false} 
                axisLine={false}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="bg-slate-950 border border-slate-850 px-3 py-2 rounded-lg shadow-2xl text-xs space-y-1">
                        <p className="text-slate-400 font-mono font-semibold border-b border-slate-800 pb-1 mb-1">
                          Date: {payload[0].payload.date}
                        </p>
                        {payload.map((item, index) => (
                          <div key={index} className="flex items-center gap-1.5 font-mono text-slate-200">
                            <span className="w-2.5 h-0.5" style={{ backgroundColor: item.color }} />
                            <span>{item.name}: {typeof item.value === 'number' ? item.value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) : item.value}</span>
                          </div>
                        ))}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Legend 
                verticalAlign="top" 
                height={36} 
                iconType="circle"
                iconSize={8}
                wrapperStyle={{ fontSize: 11, color: "#94a3b8" }}
              />
              {/* Primary metric line */}
              <Line 
                name={`Actual ${selectedMetric}`}
                type="monotone" 
                dataKey="value" 
                stroke="#8b5cf6" 
                strokeWidth={2}
                dot={{ r: 2, fill: "#8b5cf6", strokeWidth: 0 }}
                activeDot={{ r: 4, fill: "#c084fc", strokeWidth: 0 }}
              />
              {/* 3-period moving average line */}
              <Line 
                name="3-Period Moving Average"
                type="monotone" 
                dataKey="moving_average" 
                stroke="#06b6d4" 
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
                activeDot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
