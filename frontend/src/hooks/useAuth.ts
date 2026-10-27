import { useMutation, useQuery } from "@tanstack/react-query";

import { authService } from "@/services/authService";

export function useLogin() {
  return useMutation({
    mutationFn: authService.login,
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: authService.register,
  });
}

export function useCurrentUser(isAuthenticated: boolean) {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: authService.getCurrentUser,
    enabled: isAuthenticated,
    retry: false,
    staleTime: 0,
  });
}