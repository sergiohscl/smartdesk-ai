import { useQuery } from "@tanstack/react-query";
import { healthService } from "../services/healthService";

export function useApiHealth() {
  return useQuery({
    queryKey: ["api-health"],
    queryFn: healthService.check,
    refetchInterval: 30000,
    staleTime: 10000,
    retry: 1,
  });
}