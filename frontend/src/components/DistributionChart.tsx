"use client";

import React, { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip,
  Cell
} from "recharts";
import { AlertCircle, HelpCircle } from "lucide-react";

interface HistogramBin {
  bin_start: number;
  bin_end: number;
  count: number;
}

interface DistributionMetric {
  skewness: number | null;
  skewness_classification: string;
  kurtosis: number | null;
  kurtosis_classification: string;
  histogram: HistogramBin[];
}

interface DistributionChartProps {
  distributions: Record<string, DistributionMetric>;
}

export default function DistributionChart({ distributions }: DistributionChartProps) {
  const cols = Object.keys(distributions);
  const [selectedCol, setSelectedCol] = useState(cols[0] || "");

  if (cols.length === 0 || !selectedCol) {
    return (
      <Card className="border-slate-800 bg-slate-900/50 backdrop-blur-xl shadow-xl">
        <CardContent className="flex flex-col items-center justify-center p-8 text-center text-slate-400">
          <AlertCircle size={36} className="text-slate-500 mb-3" />
          <p className="font-semibold text-slate-300">No Distribution Data</p>
          <p className="text-xs max-w-xs mt-1">
            No numerical columns were identified for frequency distribution calculations.
          </p>
        </CardContent>
      </Card>
    );
  }

  const currentData = distributions[selectedCol];
  
  // Format data for Recharts: combine bin edges for X-axis labels
  const chartData = currentData.histogram.map((bin) => ({
    binName: `${bin.bin_start.toFixed(1)} - ${bin.bin_end.toFixed(1)}`,
    count: bin.count,
    range: `Range: ${bin.bin_start.toFixed(3)} to ${bin.bin_end.toFixed(3)}`
  }));

  // Define dynamic color styles based on skewness classification
  let badgeColor = "bg-slate-800 border-slate-700 text-slate-300";
  if (currentData.skewness_classification === "symmetric") {
    badgeColor = "bg-emerald-500/10 border-emerald-500/20 text-emerald-400";
  } else if (currentData.skewness_classification === "right-skewed" || currentData.skewness_classification === "left-skewed") {
    badgeColor = "bg-amber-500/10 border-amber-500/20 text-amber-400";
  }

  return (
    <Card className="border-slate-800 bg-slate-900/50 backdrop-blur-xl shadow-2xl relative overflow-hidden transition-all duration-300">
      <div className="absolute -bottom-24 -left-24 w-48 h-48 rounded-full bg-cyan-600/5 blur-3xl" />
      
      <CardHeader className="pb-3 border-b border-slate-850 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <CardTitle className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            Frequency Distribution
          </CardTitle>
          <CardDescription className="text-slate-400">
            Bin counts and shape parameters of numeric distributions
          </CardDescription>
        </div>
        
        {/* Dropdown Selector */}
        <div className="flex items-center gap-2">
          <label htmlFor="col-select" className="text-xs text-slate-400 font-medium">Select Column:</label>
          <select
            id="col-select"
            value={selectedCol}
            onChange={(e) => setSelectedCol(e.target.value)}
            className="text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 px-3 py-2 outline-none focus:border-cyan-500 transition-colors"
          >
            {cols.map((col) => (
              <option key={col} value={col}>
                {col}
              </option>
            ))}
          </select>
        </div>
      </CardHeader>
      
      <CardContent className="pt-6 space-y-6">
        {/* Descriptive Metrics Banner */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Skewness */}
          <div className="p-3 bg-slate-950/40 border border-slate-850 rounded-xl relative group">
            <div className="absolute top-2 right-2 cursor-pointer text-slate-500 hover:text-slate-400">
              <HelpCircle size={12} />
              <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1 w-48 p-2 bg-slate-950 border border-slate-800 rounded text-[10px] text-slate-300 invisible group-hover:visible transition-all duration-200 z-50 shadow-2xl">
                Skewness measures asymmetry. Zero indicates a symmetric distribution (normal curve). Positive is right-skewed; negative is left-skewed.
              </div>
            </div>
            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Skewness</p>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-lg font-bold font-mono text-white">
                {currentData.skewness !== null ? currentData.skewness.toFixed(3) : "N/A"}
              </span>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${badgeColor}`}>
                {currentData.skewness_classification}
              </span>
            </div>
          </div>

          {/* Kurtosis */}
          <div className="p-3 bg-slate-950/40 border border-slate-850 rounded-xl relative group">
            <div className="absolute top-2 right-2 cursor-pointer text-slate-500 hover:text-slate-400">
              <HelpCircle size={12} />
              <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1 w-48 p-2 bg-slate-950 border border-slate-800 rounded text-[10px] text-slate-300 invisible group-hover:visible transition-all duration-200 z-50 shadow-2xl">
                Excess Kurtosis measures tailedness. Value of 0 matches normal bell curve. Positive is heavy-tailed (outlier prone); negative is flat-tailed (outlier light).
              </div>
            </div>
            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Excess Kurtosis</p>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-lg font-bold font-mono text-white">
                {currentData.kurtosis !== null ? currentData.kurtosis.toFixed(3) : "N/A"}
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold border border-slate-700 bg-slate-800/50 text-slate-400 truncate max-w-[130px]" title={currentData.kurtosis_classification}>
                {currentData.kurtosis_classification.split(" (")[0]}
              </span>
            </div>
          </div>

          {/* Total Binned Count */}
          <div className="p-3 bg-slate-950/40 border border-slate-850 rounded-xl">
            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Valid Sample Size</p>
            <p className="text-lg font-bold font-mono text-cyan-400 mt-1">
              {currentData.histogram.reduce((acc, bin) => acc + bin.count, 0).toLocaleString()}
              <span className="text-[10px] text-slate-500 font-sans font-normal ml-1.5">rows</span>
            </p>
          </div>
        </div>

        {/* Recharts Bar Chart */}
        <div className="h-64 w-full bg-slate-950/20 border border-slate-900 rounded-xl p-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.2} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis 
                dataKey="binName" 
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
                    const data = payload[0].payload;
                    return (
                      <div className="bg-slate-950 border border-slate-850 px-3 py-2 rounded-lg shadow-2xl text-xs">
                        <p className="text-slate-400 font-mono mb-1">{data.range}</p>
                        <div className="flex items-center gap-1.5 font-bold text-white">
                          <span className="w-2 h-2 rounded-full bg-cyan-400" />
                          <span>Frequency: {payload[0].value}</span>
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar 
                dataKey="count" 
                fill="url(#colorCount)" 
                radius={[4, 4, 0, 0]}
              >
                {chartData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    className="hover:fill-cyan-400 transition-colors duration-200" 
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
