import { useAuth } from "@/store/useAuth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

if (typeof window !== "undefined" && window.location.hostname !== "localhost" && API_BASE_URL.includes("localhost")) {
  console.warn(
    "⚠️ SalesOP Warning: Deployed site is trying to call a localhost backend! " +
    "Please configure the NEXT_PUBLIC_API_URL environment variable in your Vercel project settings and trigger a Redeploy."
  );
}


export async function fetchApi(endpoint: string, options: RequestInit = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers = new Headers(options.headers || {});
  
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      // Clear credentials and force session redirection
      if (typeof window !== "undefined") {
        useAuth.getState().logout();
      }
    }
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || "An unexpected error occurred.");
  }
  
  return response.json();
}
