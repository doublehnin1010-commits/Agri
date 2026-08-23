import axios, { AxiosError } from "axios";
import { useAuthStore } from "../contexts/authStore";

function resolveApiBaseUrl(): string {
  const configured = (
    import.meta.env.VITE_API_URL ?? import.meta.env.VITE_API_BASE_URL
  )?.replace(/\/$/, "");

  if (configured) {
    const url = new URL(configured, window.location.origin);

    // An HTTPS page cannot call an HTTP API. Production APIs should expose
    // HTTPS, and this also fixes old environment values that still say http.
    if (window.location.protocol === "https:" && url.protocol === "http:") {
      url.protocol = "https:";
    }

    const pathname = url.pathname.replace(/\/$/, "");
    url.pathname = pathname.endsWith("/api/v1") ? pathname : `${pathname}/api/v1`;
    return url.toString().replace(/\/$/, "");
  }

  // Same-origin works for local Vite proxying and HTTPS deployments that
  // route /api to the backend, without introducing mixed-content requests.
  return "/api/v1";
}

const baseURL = resolveApiBaseUrl();

export function resolveApiAssetUrl(assetUrl: string): string {
  if (/^(blob:|data:|https?:)/.test(assetUrl)) return assetUrl;
  return new URL(assetUrl, `${baseURL}/`).toString();
}

export const apiClient = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  // Axios inherits the client's application/json header. Remove it for file
  // uploads so the browser can generate multipart/form-data with its required
  // boundary; otherwise FastAPI sees no form field and responds with 422.
  if (config.data instanceof FormData) {
    delete config.headers["Content-Type"];
  }

  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.dispatchEvent(new CustomEvent("auth:unauthorized"));
    }
    return Promise.reject(error);
  },
);

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError<{ detail?: unknown; message?: unknown }>(error)) {
    const detail = error.response?.data?.detail;
    const message = error.response?.data?.message;

    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const validationMessages = detail
        .map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object" && "msg" in item && typeof item.msg === "string") {
            return item.msg;
          }
          return null;
        })
        .filter((item): item is string => Boolean(item));
      if (validationMessages.length) return validationMessages.join("; ");
    }
    if (typeof message === "string") return message;
    return error.message || "Something went wrong";
  }
  return error instanceof Error ? error.message : "Something went wrong";
}
