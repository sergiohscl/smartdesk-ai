import { api } from "@/services/api";

import type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  UserPublic,
} from "@/types/auth.types";

export const authService = {
  async register(data: RegisterRequest): Promise<UserPublic> {
    const response = await api.post<UserPublic>(
      "/auth/register",
      data,
    );

    return response.data;
  },

  async login(data: LoginRequest): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>(
      "/auth/login",
      data,
    );

    return response.data;
  },

  async getCurrentUser(): Promise<UserPublic> {
    const response = await api.get<UserPublic>(
      "/users/me",
    );

    return response.data;
  },
};