"use client";

import React, { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Info, HelpCircle } from "lucide-react";

interface TrustScoreGaugeProps {
  score: number;
  breakdown: {
    completeness: number;
    consistency: number;
    anomaly_health: number;
  };
}

export default function TrustScoreGauge({ score, breakdown }: TrustScoreGaugeProps) {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    // Trigger slide-in animation on mount
    const timer = setTimeout(() => setAnimatedScore(score), 200);
    return () => clearTimeout(timer);
  }, [score]);

  // Determine color theme based on score
  let strokeColor = "stroke-rose-500";
  let textColor = "text-rose-500";
  let glowColor = "shadow-rose-500/20 border-rose-500/20";
  let statusText = "CRITICAL";

  if (score >= 71) {
    strokeColor = "stroke-emerald-500";
    textColor = "text-emerald-500";
    glowColor = "shadow-emerald-500/20 border-emerald-500/20";
    statusText = "EXCELLENT";
  } else if (score >= 41) {
    strokeColor = "stroke-amber-500";
    textColor = "text-amber-500";
    glowColor = "shadow-amber-500/20 border-amber-500/20";
    statusText = "WARNING";
  }

  // Circular calculations: radius = 35, circumference = 2 * pi * 35 = 219.91
  const radius = 35;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (circumference * animatedScore) / 100;

  return (
    <Card className={`relative overflow-hidden border bg-slate-900/50 backdrop-blur-xl shadow-2xl transition-all duration-500 ${glowColor}`}>
      {/* Decorative Gradient Glows */}
      <div className="absolute -top-24 -left-24 w-48 h-48 rounded-full bg-violet-600/10 blur-3xl" />
      <div className="absolute -bottom-24 -right-24 w-48 h-48 rounded-full bg-cyan-600/10 blur-3xl" />
      
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              Data Trust Score™
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${textColor} border-current/20 bg-current/5 animate-pulse`}>
                {statusText}
              </span>
            </CardTitle>
            <CardDescription className="text-slate-400">
              The proprietary single-metric grade of dataset reliability
            </CardDescription>
          </div>
          <div className="relative group cursor-pointer text-slate-400 hover:text-slate-200">
            <HelpCircle size={18} />
            <div className="absolute right-0 w-64 p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs shadow-2xl invisible opacity-0 group-hover:visible group-hover:opacity-100 transition-all duration-300 z-50">
              Weighted index: 40% Completeness (missing values check), 30% Consistency (mixed type check), and 30% Anomaly Health (row-level statistical outlier test).
            </div>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="flex flex-col md:flex-row items-center justify-around gap-6 py-4">
        {/* Gauge visual */}
        <div className="relative w-44 h-44 flex items-center justify-center">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
            {/* Background Track */}
            <circle
              cx="50"
              cy="50"
              r={radius}
              className="stroke-slate-800 fill-none"
              strokeWidth="6.5"
            />
            {/* Animated Gauge Ring */}
            <circle
              cx="50"
              cy="50"
              r={radius}
              className={`fill-none transition-all duration-[1500ms] cubic-bezier(0.1, 1, 0.1, 1) ${strokeColor}`}
              strokeWidth="6.5"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
            />
          </svg>
          {/* Central Score Text */}
          <div className="absolute text-center flex flex-col justify-center items-center">
            <span className="text-4xl font-extrabold tracking-tight text-white leading-none">
              {Math.round(animatedScore)}
            </span>
            <span className="text-[10px] text-slate-400 uppercase tracking-widest mt-1">
              out of 100
            </span>
          </div>
        </div>

        {/* Metric Breakdowns */}
        <div className="flex-1 w-full space-y-4 max-w-sm">
          {/* Completeness */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
                Completeness
              </span>
              <span className="font-mono text-slate-400">{breakdown.completeness}%</span>
            </div>
            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
              <div 
                className="h-full bg-indigo-500 rounded-full transition-all duration-1000 ease-out"
                style={{ width: `${breakdown.completeness}%` }}
              />
            </div>
            <p className="text-[10px] text-slate-500 pl-4">
              Ratio of non-empty data cells in the dataset.
            </p>
          </div>

          {/* Consistency */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-500" />
                Consistency
              </span>
              <span className="font-mono text-slate-400">{breakdown.consistency}%</span>
            </div>
            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
              <div 
                className="h-full bg-cyan-500 rounded-full transition-all duration-1000 ease-out"
                style={{ width: `${breakdown.consistency}%` }}
              />
            </div>
            <p className="text-[10px] text-slate-500 pl-4">
              Columns passing type-uniformity (zero mixed data types).
            </p>
          </div>

          {/* Anomaly Health */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                Anomaly Health
              </span>
              <span className="font-mono text-slate-400">{breakdown.anomaly_health}%</span>
            </div>
            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
              <div 
                className="h-full bg-rose-500 rounded-full transition-all duration-1000 ease-out"
                style={{ width: `${breakdown.anomaly_health}%` }}
              />
            </div>
            <p className="text-[10px] text-slate-500 pl-4">
              Percentage of rows free of z-score statistical anomalies.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
