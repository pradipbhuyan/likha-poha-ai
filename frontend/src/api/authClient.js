import { supabase } from "./supabaseClient";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function authFetch(path, options = {}) {
  const { data, error } = await supabase.auth.getSession();

  if (error) {
    throw new Error("Unable to read Supabase session");
  }

  let token = data.session?.access_token;

  if (!token) {
    const refreshed = await supabase.auth.refreshSession();
    token = refreshed.data.session?.access_token;
  }

  if (!token) {
    throw new Error("No Supabase access token found. Please logout and login again.");
  }

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
    Authorization: `Bearer ${token}`,
  };

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = "API request failed";
  
    try {
      const errorData = await response.json();
      message = errorData.detail || errorData.message || message;
    } catch {
      const errorText = await response.text();
      message = errorText || message;
    }
  
    throw new Error(message);
  }

  return response.json();
}