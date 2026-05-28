import { supabase } from "./supabaseClient";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

export async function authFetch(path, options = {}) {
  const { data } = await supabase.auth.getSession();

  const token = data.session?.access_token;

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    throw new Error(`API failed: ${path}`);
  }

  return response.json();
}