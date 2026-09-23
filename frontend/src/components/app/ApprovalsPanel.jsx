import React, { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ShieldAlert, Check, X, Loader2 } from "lucide-react";
import { toast } from "sonner";

export function ApprovalsPanel({ companyId, onDone }) {
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState("");

  const load = useCallback(() => {
    const params = { status: "pending" };
    if (companyId) params.company_id = companyId;
    api.get("/actions", { params }).then((r) => setRows(r.data.actions || []));
  }, [companyId]);
  useEffect(() => { load(); }, [load]);

  const decide = async (id, ok) => {
    setBusy(id);
    try {
      const r = await api.post(`/actions/${id}/${ok ? "approve" : "reject"}`);
      const a = r.data;
      if (a.status === "done") toast.success(`Bajarildi: ${a.description}${a.result?.ref_key ? ` · Ref ${a.result.ref_key}` : ""}`);
      else if (a.status === "rejected") toast("Bekor qilindi");
      else toast.error(a.error || "Bajarilmadi");
      load(); onDone?.();
    } catch (e) { toast.error(e?.response?.data?.detail || "Xatolik"); }
    finally { setBusy(""); }
  };

  if (rows.length === 0) return null;
  return (
    <div className="border border-amber-300 bg-amber-50/60 dark:bg-amber-950/30 rounded-sm p-4 space-y-2" data-testid="approvals-panel">
      <div className="flex items-center gap-2 font-medium text-sm"><ShieldAlert className="h-4 w-4 text-amber-600" /> Tasdiq kutilmoqda ({rows.length})</div>
      {rows.map((a) => (
        <div key={a.id} className="flex items-center gap-3 bg-background border rounded-sm px-3 py-2" data-testid={`action-row-${a.id}`}>
          <Badge variant="outline" className="rounded-sm text-xs shrink-0">{a.label}</Badge>
          <span className="text-sm flex-1 min-w-0 truncate">{a.description}</span>
          <span className="text-xs text-muted-foreground">{a.source}</span>
          <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 h-8" disabled={!!busy} onClick={() => decide(a.id, true)} data-testid={`approve-${a.id}`}>
            {busy === a.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
          </Button>
          <Button size="sm" variant="outline" className="h-8" disabled={!!busy} onClick={() => decide(a.id, false)} data-testid={`reject-${a.id}`}>
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      ))}
    </div>
  );
}
