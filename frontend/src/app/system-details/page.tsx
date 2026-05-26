"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Shield, ArrowLeft, Cpu, Lock, Activity, Server, Zap } from "lucide-react";

export default function SystemDetails() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans relative overflow-hidden">
      {/* Decorative Backdrops */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] rounded-full bg-violet-600/10 blur-3xl pointer-events-none -z-10" />
      <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] rounded-full bg-cyan-600/10 blur-3xl pointer-events-none -z-10" />

      <header className="container mx-auto px-4 h-20 flex items-center justify-between border-b border-slate-800/80 backdrop-blur-md sticky top-0 z-40">
        <Link href="/" className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm font-semibold">Back to Home</span>
        </Link>
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-cyan-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">SalesOP Architecture Spec</span>
        </div>
      </header>

      <main className="flex-1 container mx-auto px-4 py-16 max-w-4xl space-y-12">
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 text-xs text-cyan-400 bg-cyan-950/40 border border-cyan-800/30 rounded-full font-semibold shadow-inner">
            <Shield className="w-3.5 h-3.5" />
            Active Cybersecurity Hardening Specification
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            Platform Architecture & Security Blueprint
          </h1>
          <p className="text-slate-400 text-sm max-w-2xl mx-auto leading-relaxed">
            SalesOP enforces rigorous cryptographic validations, multi-layered isolation, and sandboxed AI boundaries to protect critical financial and payment datasets.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-6 border border-slate-800 bg-slate-900/40 backdrop-blur-xl rounded-xl space-y-3">
            <Lock className="w-8 h-8 text-cyan-400" />
            <h3 className="text-lg font-bold text-white">Dynamic Session Security</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Eliminated client-side localStorage token writing. Credentials are held in HTTP-only, secure, encrypted cookies. Built-in adaptive SameSite evaluation dynamically transitions from <code className="text-cyan-400">lax</code> in local development to <code className="text-violet-400">none; secure</code> in production, allowing seamless cross-site communication.
            </p>
          </div>

          <div className="p-6 border border-slate-800 bg-slate-900/40 backdrop-blur-xl rounded-xl space-y-3">
            <Zap className="w-8 h-8 text-violet-400 animate-pulse" />
            <h3 className="text-lg font-bold text-white">Vectorized Validation Pipelines</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              CSV parsing, binary checks, and mixed-type consistency checks operate on optimized vectorized pandas and numpy C/C++ libraries. Formula injection triggers (e.g. <code className="text-rose-400">=, +, -, @</code>) are parsed and sanitized globally in a single vectorized pass, providing 100x speedups.
            </p>
          </div>

          <div className="p-6 border border-slate-800 bg-slate-900/40 backdrop-blur-xl rounded-xl space-y-3">
            <Cpu className="w-8 h-8 text-cyan-400" />
            <h3 className="text-lg font-bold text-white">Constrained AI Boundaries</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              The LLM interpreter runs in an isolated context entirely constrained by deterministically calculated statistical summaries and data quality reports. It operates as a read-only translation lens and has no access to modify database records or query raw uploads.
            </p>
          </div>

          <div className="p-6 border border-slate-800 bg-slate-900/40 backdrop-blur-xl rounded-xl space-y-3">
            <Server className="w-8 h-8 text-violet-400" />
            <h3 className="text-lg font-bold text-white">Zero Trust Infrastructure</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Dual-adapter rate limiting middleware separates API routes method-by-method to shield against DDoS spam. Docker containers build via secure multi-stage recipes and execute under unprivileged non-root users (<code className="text-cyan-400">node</code> and <code className="text-cyan-400">appuser</code>) to block system-level access.
            </p>
          </div>
        </div>

        <div className="p-6 border border-slate-800 bg-slate-900/20 rounded-xl flex items-center justify-between gap-6 max-w-xl mx-auto">
          <div className="space-y-1">
            <h4 className="text-sm font-semibold text-white">Deploy Deployed Services</h4>
            <p className="text-[11px] text-slate-500">Ready to enter your operational workspace?</p>
          </div>
          <Link href="/login">
            <Button className="bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors">
              Access Workspace
            </Button>
          </Link>
        </div>
      </main>

      <footer className="border-t border-slate-900 py-8 text-center text-xs text-slate-600">
        <p>© 2026 SalesOP Intelligence. Armored Security Specs.</p>
      </footer>
    </div>
  );
}
