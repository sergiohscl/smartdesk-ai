const TOKEN_KEY = "smartdesk_access_token";

export const authToken = {
  get(): string | null {
    return sessionStorage.getItem(TOKEN_KEY);
  },

  set(token: string): void {
    sessionStorage.setItem(TOKEN_KEY, token);
  },

  clear(): void {
    sessionStorage.removeItem(TOKEN_KEY);
  },

  isAuthenticated(): boolean {
    return this.get() !== null;
  },
};