import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

const CompanyContext = createContext(null);
export const useCompany = () => useContext(CompanyContext);

export function CompanyProvider({ children }) {
  const { user } = useAuth();
  const [companies, setCompanies] = useState([]);
  const [activeId, setActiveId] = useState(() => localStorage.getItem("ai_bux_company") || null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const { data } = await api.get("/companies");
      setCompanies(data.companies || []);
      if (!activeId && data.companies?.length) {
        setActiveId(data.companies[0].id);
        localStorage.setItem("ai_bux_company", data.companies[0].id);
      }
      if (activeId && !data.companies.find((c) => c.id === activeId)) {
        const next = data.companies[0]?.id || null;
        setActiveId(next);
        if (next) localStorage.setItem("ai_bux_company", next);
        else localStorage.removeItem("ai_bux_company");
      }
    } finally {
      setLoading(false);
    }
  }, [user, activeId]);

  useEffect(() => { refresh(); }, [user]); // eslint-disable-line

  const setActive = (id) => {
    setActiveId(id);
    if (id) localStorage.setItem("ai_bux_company", id);
    else localStorage.removeItem("ai_bux_company");
  };

  const active = companies.find((c) => c.id === activeId) || null;

  return (
    <CompanyContext.Provider value={{ companies, active, activeId, setActive, refresh, loading }}>
      {children}
    </CompanyContext.Provider>
  );
}
