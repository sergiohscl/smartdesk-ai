import axios from "axios";

import { authToken } from "@/lib/authToken";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = authToken.get();

  if (token) {
    config.headers.set(
      "Authorization",
      `Bearer ${token}`,
    );
  }

  return config;
});