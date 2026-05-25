import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Shield, Activity, Database, Lock } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="container mx-auto px-4 h-20 flex items-center justify-between border-b border-border/50">
        <div className="flex items-center gap-2">
          <Activity className="w-6 h-6 text-primary" />
          <h1 className="text-xl font-bold tracking-tight">OpIntel Platform</h1>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/login">
            <Button variant="ghost">Login</Button>
          </Link>
          <Link href="/login">
            <Button>Secure Access</Button>
          </Link>
        </div>
      </header>
      
      <main className="flex-1 flex flex-col items-center justify-center text-center px-4 py-20">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 mb-8 text-sm text-primary bg-primary/10 rounded-full font-medium">
          <Shield className="w-4 h-4" />
          Zero Trust Architecture
        </div>
        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight max-w-4xl text-foreground mb-6">
          Trusted Operational Intelligence.
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl mb-10 leading-relaxed">
          Deterministic analytics enhanced by constrained AI interpretation. 
          Upload datasets securely and get instant, reliable operational insights without risking data privacy.
        </p>
        <div className="flex items-center gap-4">
          <Link href="/login">
            <Button size="lg" className="h-12 px-8 text-md">Enter Workspace</Button>
          </Link>
          <Link href="/system-details">
            <Button size="lg" variant="outline" className="h-12 px-8 text-md">Platform Architecture</Button>
          </Link>
        </div>
        
        <div className="grid md:grid-cols-3 gap-8 mt-24 max-w-5xl mx-auto text-left">
          <div className="p-6 border border-border rounded-xl bg-card">
            <Database className="w-10 h-10 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Deterministic Validation</h3>
            <p className="text-muted-foreground leading-relaxed">
              Every dataset undergoes strict statistical analysis before AI interpretation, ensuring no hallucinations.
            </p>
          </div>
          <div className="p-6 border border-border rounded-xl bg-card">
            <Lock className="w-10 h-10 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Constrained Intelligence</h3>
            <p className="text-muted-foreground leading-relaxed">
              AI acts only as an interpretation layer. It never touches raw uploads or makes unverified claims.
            </p>
          </div>
          <div className="p-6 border border-border rounded-xl bg-card">
            <Shield className="w-10 h-10 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Zero Trust Security</h3>
            <p className="text-muted-foreground leading-relaxed">
              Strict MIME validation, parameter sanitization, and size limits protect against hostile payloads.
            </p>
          </div>
        </div>
      </main>
      
      <footer className="border-t py-8 text-center text-muted-foreground">
        <p>© 2026 Operational Intelligence Platform. Enterprise-Grade Security.</p>
      </footer>
    </div>
  );
}
