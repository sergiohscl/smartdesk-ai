export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export type UserRole = "user" | "support" | "admin";

export interface UserPublic {
  id: number;
  name: string;
  email: string;
  is_active: boolean;
  role: UserRole;
  created_at: string;
}
