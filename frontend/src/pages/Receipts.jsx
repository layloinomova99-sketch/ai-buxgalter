import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useCompany } from "@/context/CompanyContext";
import { Badge } from "@/components/ui/badge";
import { Receipt } from "lucide-react";

const STATUS_CLASSES = {
  received: "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-900 dark:text-slate-300 dark:border-slate-800",
  parsed: "bg-cyan-50 text-cyan-700 border-cyan-200 dark:bg-cyan-950 dark:text-cyan-400 dark:border-cyan-900",
  matched: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-900",
  needs_review: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-900",
  approved: "bg-teal-50 text-teal-700 border-teal-200 dark:bg-teal-950 dark:text-teal-400 dark:border-teal-900",
  imported: "bg-neutral-900 text-white border-neutral-950 dark:bg-white dark:text-black dark:border-neutral-200",
  failed: "bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-400 dark:border-red-900",
  duplicate: "bg-stone-100 text-stone-600 border-stone-200 dark:bg-stone-900 dark:text-stone-400 dark:border-stone-800",
};

export default function Receipts() {
  const { active } = useCompany();
  const [rows, setRows] = useState([]);

  useEffect(() => {
    if (!active) return;
    api.get(`/companies/${active.id}/receipts`).then((r) => setRows(r.data.receipts || []));
  }, [active]);

  if (!active) return <div className="p-8 text-muted-foreground">Kompaniyani tanlang.</div>;

  return (
    <div className="p-6 md:p-8 space-y-6">
      <div>
        <h1 className="font-heading text-3xl font-bold tracking-tight">Cheklar</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Soliq integratsiyasi Creator tomonidan sozlangandan keyin cheklar avtomatik yuklanadi.
        </p>
      </div>

      {rows.length === 0 ? (
        <div className="border-2 border-dashed rounded-sm p-12 text-center" data-testid="empty-receipts">
          <Receipt className="h-10 w-10 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">Hozircha cheklar yo'q</p>
          <p className="text-xs text-muted-foreground mt-2">
            Soliq ulanishi Creator tomonidan aniqlangan workflowda ishlaydi
          </p>
        </div>
      ) : (
        <div className="border rounded-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase tracking-widest">
              <tr>
                <th className="text-left px-4 py-3">Manba</th>
                <th className="text-left px-4 py-3">Raqam</th>
                <th className="text-left px-4 py-3">Sana</th>
                <th className="text-right px-4 py-3">Summa</th>
                <th className="text-left px-4 py-3">Holat</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-t hover:bg-muted/30" data-testid={`receipt-row-${r.id}`}>
                  <td className="px-4 py-3">{r.source}</td>
                  <td className="px-4 py-3 font-mono text-xs">{r.receipt_number || r.external_id || "—"}</td>
                  <td className="px-4 py-3">{r.sale_date || "—"}</td>
                  <td className="px-4 py-3 text-right font-mono">{Number(r.total_amount || 0).toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <Badge className={`rounded-sm border ${STATUS_CLASSES[r.status] || ""}`}>{r.status}</Badge>
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
