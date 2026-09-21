import React, { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("ai_bux_user");
    return raw ? JSON.parse(raw) : null;
  });
  const [loading, setLoading] = useState(false);

  const persist = (token, u) => {
    localStorage.setItem("ai_bux_token", token);
    localStorage.setItem("ai_bux_user", JSON.stringify(u));
    setUser(u);
  };

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    persist(data.token, data.user);
    return data.user;
  };

  const register = async (payload) => {
    const { data } = await api.post("/auth/register", payload);
    persist(data.token, data.user);
    return data.user;
  };

  const logout = () => {
    localStorage.removeItem("ai_bux_token");
    localStorage.removeItem("ai_bux_user");
    setUser(null);
  };

  useEffect(() => {
    const t = localStorage.getItem("ai_bux_token");
    if (t && !user) {
      setLoading(true);
      api.get("/auth/me").then((r) => {
        localStorage.setItem("ai_bux_user", JSON.stringify(r.data));
        setUser(r.data);
      }).catch(() => {}).finally(() => setLoading(false));
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
