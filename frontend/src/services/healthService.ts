import { api } from "./api";

export interface HealthResponse {
  status: string;
}

export const healthService = {
  async check(): Promise<HealthResponse> {
    const { data } =
      await api.get<HealthResponse>("/api/v1/health");

    return data;
  },
};