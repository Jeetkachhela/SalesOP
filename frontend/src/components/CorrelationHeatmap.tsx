"use client";

import React, { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, TrendingUp, HelpCircle } from "lucide-react";

interface CorrelationHeatmapProps {
  matrix: Record<string, Record<string, number | null>>;
  strongCorrelations: Array<{
    col_a: string;
    col_b: string;
    coefficient: number;
    direction: "positive" | "negative";
  }>;
}

export default function CorrelationHeatmap({ matrix, strongCorrelations }: CorrelationHeatmapProps) {
  const [hoveredCell, setHoveredCell] = useState<{
    colA: string;
    colB: string;
    val: number | null;
  } | null>(null);

  const cols = Object.keys(matrix);

  if (cols.length === 0) {
    return (
      <Card className="border-slate-800 bg-slate-900/50 backdrop-blur-xl shadow-xl">
        <CardContent className="flex flex-col items-center justify-center p-8 text-center text-slate-400">
          <AlertCircle size={36} className="text-slate-500 mb-3" />
          <p className="font-semibold text-slate-300">Insufficient Numerical Data</p>
          <p className="text-xs max-w-xs mt-1">
            We need at least 2 numeric columns to calculate Pearson correlation coefficients.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Get color for correlation value (-1 to +1)
  const getCellColor = (val: number | null): React.CSSProperties => {
    if (val === null) {
      return {
        backgroundColor: "rgba(2, 6, 23, 0.2)",
        color: "#475569"
      };
    }
    
    // Scale intensity between 0 and 1
    const intensity = Math.min(1.0, Math.abs(val));
    
    if (val > 0) {
      // Red for positive correlation
      return {
        backgroundColor: `rgba(239, 68, 68, ${intensity * 0.85})`,
        color: intensity > 0.4 ? "#fff" : "#94a3b8"
      };
    } else if (val < 0) {
      // Blue for negative correlation
      return {
        backgroundColor: `rgba(59, 130, 246, ${intensity * 0.85})`,
        color: intensity > 0.4 ? "#fff" : "#94a3b8"
      };
    }
    
    return {
      backgroundColor: "transparent",
      color: "#64748b"
    };
  };

  return (
    <Card className="border-slate-800 bg-slate-900/50 backdrop-blur-xl shadow-2xl relative overflow-hidden transition-all duration-300 hover:shadow-cyan-950/10">
      <div className="absolute -top-24 -right-24 w-48 h-48 rounded-full bg-rose-600/5 blur-3xl" />
      
      <CardHeader className="pb-3 border-b border-slate-850">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              Linear Correlation Matrix
            </CardTitle>
            <CardDescription className="text-slate-400">
              Pearson coefficients indicating direction and strength of relationship
            </CardDescription>
          </div>
          <div className="relative group cursor-pointer text-slate-400 hover:text-slate-200">
            <HelpCircle size={18} />
            <div className="absolute right-0 w-64 p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs shadow-2xl invisible opacity-0 group-hover:visible group-hover:opacity-100 transition-all duration-300 z-50">
              Pearson correlation coefficient (r) ranges from -1.0 (perfect negative correlation) to +1.0 (perfect positive correlation). Values close to 0 suggest no linear relationship.
            </div>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="pt-6 space-y-6">
        {/* Heatmap Grid container */}
        <div className="w-full overflow-x-auto pb-2 scrollbar-thin">
          <div className="min-w-[480px]">
            {/* Headers Row */}
            <div className="flex items-center">
              {/* Corner spacer */}
              <div className="w-32 flex-shrink-0 text-[10px] uppercase font-bold text-slate-500 pr-2 truncate text-right">
                Columns
              </div>
              <div className="flex flex-1">
                {cols.map((col) => (
                  <div 
                    key={`header-${col}`} 
                    className="flex-1 text-center text-[10px] font-bold text-slate-400 px-1 py-1 truncate cursor-default select-none border-b border-slate-800"
                    title={col}
                  >
                    {col}
                  </div>
                ))}
              </div>
            </div>
            
            {/* Grid rows */}
            <div className="space-y-[2px] mt-[4px]">
              {cols.map((rowCol) => (
                <div key={`row-${rowCol}`} className="flex items-center">
                  {/* Row title */}
                  <div 
                    className="w-32 flex-shrink-0 text-right text-xs font-bold text-slate-400 pr-3 truncate cursor-default"
                    title={rowCol}
                  >
                    {rowCol}
                  </div>
                  
                  {/* Grid cells */}
                  <div className="flex flex-1 gap-[2px]">
                    {cols.map((colCol) => {
                      const val = matrix[rowCol]?.[colCol] ?? null;
                      const styleInfo = getCellColor(val);
                      const isSelf = rowCol === colCol;
                      
                      return (
                        <div
                          key={`cell-${rowCol}-${colCol}`}
                          className={`flex-1 aspect-square md:h-10 flex items-center justify-center text-[10px] font-mono font-semibold rounded-[2px] border border-slate-900/10 cursor-pointer select-none transition-all duration-150 hover:scale-[1.08] hover:z-10 hover:shadow-lg`}
                          style={isSelf ? { backgroundColor: "rgba(100, 116, 139, 0.15)", color: "#94a3b8" } : styleInfo}
                          onMouseEnter={() => setHoveredCell({ colA: rowCol, colB: colCol, val })}
                          onMouseLeave={() => setHoveredCell(null)}
                          title={`${rowCol} × ${colCol}: ${val !== null ? val : "N/A"}`}
                        >
                          {val !== null ? val.toFixed(2) : "-"}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Live Hover Tooltip Panel */}
        <div className="h-10 bg-slate-950/40 rounded-lg border border-slate-800/40 flex items-center justify-center px-4 text-xs">
          {hoveredCell ? (
            <div className="flex items-center gap-2 text-slate-300">
              <span className="font-bold text-cyan-400">{hoveredCell.colA}</span>
              <span className="text-slate-500">×</span>
              <span className="font-bold text-cyan-400">{hoveredCell.colB}</span>
              <span className="text-slate-500">:</span>
              {hoveredCell.colA === hoveredCell.colB ? (
                <span className="font-mono bg-slate-800/50 px-1.5 py-0.5 rounded text-slate-400">1.00 (Self)</span>
              ) : hoveredCell.val !== null ? (
                <span className={`font-mono font-bold px-1.5 py-0.5 rounded ${
                  hoveredCell.val > 0 ? "text-rose-400 bg-rose-500/10" : "text-blue-400 bg-blue-500/10"
                }`}>
                  {hoveredCell.val > 0 ? "+" : ""}{hoveredCell.val.toFixed(4)} ({
                    Math.abs(hoveredCell.val) > 0.7 
                      ? "Strong Correlation" 
                      : Math.abs(hoveredCell.val) > 0.4 
                      ? "Moderate Correlation" 
                      : "Weak Correlation"
                  })
                </span>
              ) : (
                <span className="text-slate-500 italic">No linear correlation</span>
              )}
            </div>
          ) : (
            <span className="text-slate-500 italic">Hover over any cell to see detailed correlation coefficient</span>
          )}
        </div>

        {/* Strong correlations checklist */}
        <div className="space-y-2 border-t border-slate-850 pt-4">
          <h4 className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
            <TrendingUp size={14} className="text-indigo-400" />
            Key Correlation Insights
          </h4>
          
          {strongCorrelations.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {strongCorrelations.map((sc, idx) => (
                <div 
                  key={`strong-${idx}`}
                  className="flex items-center gap-3 p-2.5 bg-slate-900 border border-slate-800 rounded-lg text-xs"
                >
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    sc.direction === "positive" ? "bg-rose-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]" : "bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]"
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-slate-200 truncate">
                      {sc.col_a} <span className="text-slate-500">&amp;</span> {sc.col_b}
                    </p>
                    <p className="text-[10px] text-slate-400 mt-0.5">
                      Strong {sc.direction} coefficient: <span className="font-mono text-white">{sc.coefficient}</span>
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500 italic">
              No highly correlated column pairs detected (|r| &gt; 0.7). The fields in this dataset represent independent metrics, which is excellent for statistical model modeling stability.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
