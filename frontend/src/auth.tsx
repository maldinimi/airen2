import { createContext, type ReactNode, useContext, useEffect, useState } from "react";
import { api, setCsrf } from "./api";
import type { Pengguna, Role } from "./types";

type Auth = {
  pengguna: Pengguna | null;
  memuat: boolean;
  masuk: (username: string, password: string) => Promise<void>;
  keluar: () => Promise<void>;
  punya: (...roles: Role[]) => boolean;
};

const Ctx = createContext<Auth>(null as unknown as Auth);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [pengguna, setPengguna] = useState<Pengguna | null>(null);
  const [memuat, setMemuat] = useState(true);

  useEffect(() => {
    api.get<Pengguna>("/api/auth/saya")
      .then((p) => { setCsrf(p.csrf ?? ""); setPengguna(p); })
      .catch(() => setPengguna(null))
      .finally(() => setMemuat(false));
  }, []);

  const nilai: Auth = {
    pengguna, memuat,
    masuk: async (username, password) => {
      const p = await api.post<Pengguna>("/api/auth/login", { username, password });
      setCsrf(p.csrf ?? "");
      setPengguna(p);
    },
    keluar: async () => {
      await api.post("/api/auth/logout").catch(() => undefined);
      setPengguna(null);
      location.href = "/login";
    },
    punya: (...roles) => !!pengguna && roles.some((r) => pengguna.roles.includes(r)),
  };
  return <Ctx.Provider value={nilai}>{children}</Ctx.Provider>;
}
