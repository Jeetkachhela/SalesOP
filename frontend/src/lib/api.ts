import { useAuth } from "@/store/useAuth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

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
