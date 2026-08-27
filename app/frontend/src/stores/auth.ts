import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export interface AuthUser {
  name: string;
  username: string | null;
  initials: string;
  photoUrl: string | null;
}

interface AuthState {
  loggedIn: boolean;
  user: AuthUser | null;
  token: string | null;
  banned: boolean;
  isAdmin: boolean;
  login: (user: AuthUser) => void;
  setToken: (token: string | null) => void;
  setBanned: (banned: boolean) => void;
  setAdmin: (isAdmin: boolean) => void;
  logout: () => void;
}

export function makeAuthUser(
  firstName: string,
  lastName?: string | null,
  username?: string | null,
  photoUrl?: string | null,
): AuthUser {
  const parts = [firstName, lastName].filter((part): part is string => Boolean(part));
  const name = parts.join(" ");
  const initials = parts.map((part) => part.charAt(0).toUpperCase()).join("");
  return { name, username: username || null, initials: initials || "?", photoUrl: photoUrl || null };
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      loggedIn: false,
      user: null,
      token: null,
      banned: false,
      isAdmin: false,
      login: (user) => set({ loggedIn: true, user }),
      setToken: (token) => set({ token }),
      setBanned: (banned) => set({ banned }),
      setAdmin: (isAdmin) => set({ isAdmin }),
      logout: () => set({ loggedIn: false, user: null, token: null, banned: false, isAdmin: false }),
    }),
    {
      name: "mtp-auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ loggedIn: state.loggedIn, user: state.user, token: state.token }),
      skipHydration: true,
    },
  ),
);
