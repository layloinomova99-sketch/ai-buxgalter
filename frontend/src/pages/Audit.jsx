import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useCompany } from "@/context/CompanyContext";
import { useAuth } from "@/context/AuthContext";
import { ShieldCheck } from "lucide-react";

export default function Audit() {
  const { active } = useCompany();
  const { user } = useAuth();
  const [rows, setRows] = useState([]);

  useEffect(() => {
    const params = {};
    if (active) params.company_id = active.id;
    if (!active && user?.role !== "creator") return;
    api.get("/audit", { params }).then((r) => setRows(r.data.audit_logs || []));
  }, [active, user]);

  return (
    <div className="p-6 md:p-8 space-y-6">
      <div>
        <h1 className="font-heading text-3xl font-bold tracking-tight">Audit loglari</h1>
        <p className="text-sm text-muted-foreground mt-1">Barcha muhim harakatlar yozib boriladi</p>
      </div>
      {rows.length === 0 ? (
        <div className="border-2 border-dashed rounded-sm p-12 text-center">
          <ShieldCheck className="h-10 w-10 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">Loglar bo'sh</p>
        </div>
      ) : (
        <div className="border rounded-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase tracking-widest">
              <tr>
                <th className="text-left px-4 py-3">Vaqt</th>
                <th className="text-left px-4 py-3">Kim</th>
                <th className="text-left px-4 py-3">Nima</th>
                <th className="text-left px-4 py-3">Manba</th>
                <th className="text-left px-4 py-3">Ma'lumot</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr key={a.id} className="border-t hover:bg-muted/30" data-testid={`audit-row-${a.id}`}>
                  <td className="px-4 py-3 font-mono text-xs">{a.when}</td>
                  <td className="px-4 py-3 font-mono text-xs">{a.who?.slice(0, 8)}...</td>
                  <td className="px-4 py-3">{a.what}</td>
                  <td className="px-4 py-3">{a.source}</td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground max-w-md truncate">
                    {a.new_value ? JSON.stringify(a.new_value) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
