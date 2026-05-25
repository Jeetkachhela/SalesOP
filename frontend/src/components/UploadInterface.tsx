"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchApi } from "@/lib/api";
import { UploadCloud, FileType, CheckCircle2, AlertCircle } from "lucide-react";
import { useAuth } from "@/store/useAuth";
import { toast } from "sonner";

export default function UploadInterface({ onUploadSuccess }: { onUploadSuccess?: () => void }) {
  const { token } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    
    // Strict MVP Limit Check
    if (file.size > 50 * 1024 * 1024) {
      toast.error("File size exceeds 50MB limit");
      return;
    }
    
    if (file.type !== "text/csv" && file.type !== "application/vnd.ms-excel") {
      toast.error("Only CSV files are allowed");
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      // Direct fetch bypasses fetchApi wrapper slightly to handle FormData
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const response = await fetch(`${apiBaseUrl}/uploads/`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: formData
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Upload failed");
      }
      
      toast.success("Dataset uploaded successfully. Analysis starting...");
      setFile(null);
      if (onUploadSuccess) onUploadSuccess();
    } catch (err: any) {
      toast.error(err.message || "Failed to upload dataset.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Card className="w-full max-w-lg mx-auto bg-card text-card-foreground shadow-lg border border-border">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UploadCloud className="w-5 h-5 text-primary" />
          Upload Dataset
        </CardTitle>
        <CardDescription>
          Securely upload CSV datasets for deterministic analysis. Limit: 50MB.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <label className="flex flex-col items-center justify-center w-full h-40 border-2 border-dashed rounded-lg cursor-pointer bg-muted/50 hover:bg-muted transition-colors border-border">
          <div className="flex flex-col items-center justify-center pt-5 pb-6">
            <FileType className="w-10 h-10 text-muted-foreground mb-3" />
            <p className="mb-2 text-sm text-muted-foreground">
              <span className="font-semibold text-primary">Click to upload</span> or drag and drop
            </p>
            <p className="text-xs text-muted-foreground">CSV only (MAX. 50MB)</p>
          </div>
          <input type="file" className="hidden" accept=".csv" onChange={handleFileChange} />
        </label>
        
        {file && (
          <div className="flex items-center justify-between p-3 border rounded-md bg-background">
            <span className="text-sm font-medium truncate max-w-[200px]">{file.name}</span>
            <span className="text-xs text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
          </div>
        )}

        <Button 
          className="w-full" 
          onClick={handleUpload} 
          disabled={!file || isUploading}
        >
          {isUploading ? "Uploading & Validating..." : "Process Dataset"}
        </Button>
      </CardContent>
    </Card>
  );
}
