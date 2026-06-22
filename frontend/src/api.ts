import axios, { AxiosError } from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("aiops_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("aiops_token");
      localStorage.removeItem("aiops_user");
      if (window.location.pathname !== "/login" && window.location.pathname !== "/signup") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export function getWsBaseUrl(): string {
  return baseURL.startsWith("https")
    ? baseURL.replace("https", "wss")
    : baseURL.replace("http", "ws");
}
