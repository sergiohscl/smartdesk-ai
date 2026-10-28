import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import axios from "axios";
import { useQueryClient } from "@tanstack/react-query";

import type { ReactNode } from "react";

import { authToken } from "@/lib/authToken";
import { authService } from "@/services/authService";
import { api } from "@/services/api";

import type {
  LoginRequest,
  UserPublic,
} from "@/types/auth.types";

interface AuthContextType {
  user: UserPublic | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isInitializing: boolean;
  login: (data: LoginRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({
  children,
}: {
  children: ReactNode;
}) {
  const queryClient = useQueryClient();

  const [user, setUser] = useState<UserPublic | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);

  const logout = useCallback(() => {
    authToken.clear();
    setUser(null);

    void queryClient.cancelQueries();
    queryClient.clear();
  }, [queryClient]);

  const login = useCallback(
    async (data: LoginRequest) => {
      setIsLoading(true);

      try {
        const response = await authService.login(data);

        authToken.set(response.access_token);

        const currentUser =
          await authService.getCurrentUser();

        queryClient.clear();
        setUser(currentUser);
      } catch (error) {
        logout();
        throw error;
      } finally {
        setIsLoading(false);
      }
    },
    [logout, queryClient],
  );

  useEffect(() => {
    let active = true;

    async function restoreSession() {
      const token = authToken.get();

      if (!token) {
        setIsInitializing(false);
        return;
      }

      try {
        const currentUser =
          await authService.getCurrentUser();

        if (active) {
          setUser(currentUser);
        }
      } catch {
        if (active) {
          logout();
        }
      } finally {
        if (active) {
          setIsInitializing(false);
        }
      }
    }

    void restoreSession();

    return () => {
      active = false;
    };
  }, [logout]);

  useEffect(() => {
    const interceptor = api.interceptors.response.use(
      (response) => response,
      (error: unknown) => {
        if (
          axios.isAxiosError(error) &&
          error.response?.status === 401 &&
          authToken.get() !== null &&
          error.config?.headers?.has("Authorization")
        ) {
          logout();
        }

        return Promise.reject(error);
      },
    );

    return () => {
      api.interceptors.response.eject(interceptor);
    };
  }, [logout]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: user !== null,
        isLoading,
        isInitializing,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth deve ser utilizado dentro de AuthProvider",
    );
  }

  return context;
}