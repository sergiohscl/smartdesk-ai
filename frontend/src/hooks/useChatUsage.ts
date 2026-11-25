import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/app/providers/AuthProvider";
import { chatQueryKeys } from "@/lib/chatQueryKeys";
import { chatService } from "@/services/chatService";

export function useChatUsage() {
  const { user } = useAuth();
  const userId = user?.id ?? 0;

  return useQuery({
    queryKey: chatQueryKeys.usage(userId),
    queryFn: ({ signal }) =>
      chatService.getUsage(signal),
    enabled: userId > 0,
    staleTime: 15_000,
    retry: false,
  });
}
