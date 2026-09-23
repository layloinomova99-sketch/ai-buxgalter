import React, { useEffect, useRef, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { useCompany } from "@/context/CompanyContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Receipt, Upload, Loader2, Send } from "lucide-react";
import { toast } from "sonner";
import { ApprovalsPanel } from "@/components/app/ApprovalsPanel";
import { ReceiptDetailDialog } from "@/components/app/ReceiptDetailDialog";

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
const STATUS_UZ = { parsed: "o'qildi", matched: "moslashgan", needs_review: "ko'rib chiqish", imported: "1C da", failed: "xato", approved: "tasdiqlangan" };

export default function Receipts() {
  const { active } = useCompany();
  const [rows, setRows] = useState([]);
  const [sel, setSel] = useState({});
  const [uploading, setUploading] = useState(false);
  const [detail, setDetail] = useState(null);
  const [tick, setTick] = useState(0);
  const fileRef = useRef(null);

  const load = useCallback(() => {
    if (!active) return;
    api.get(`/companies/${active.id}/receipts`).then((r) => setRows(r.data.receipts || []));
  }, [active]);
  useEffect(() => { load(); setSel({}); }, [load]);

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const fd = new FormData(); fd.append("file", file);
    try {
      const r = await api.post(`/companies/${active.id}/soliq/upload`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(`${r.data.created} chek yuklandi · ${r.data.matched} moslashgan · ${r.data.needs_review} ko'rib chiqish · ${r.data.duplicates} takror`);
      load();
    } catch (err) { toast.error(err?.response?.data?.detail || "Xatolik"); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
  };

  const ready = rows.filter((r) => sel[r.id] && (r.status === "matched" || r.status === "failed"));
  const sendTo1C = async () => {
    try {
      const r = await api.post(`/companies/${active.id}/receipts/import-1c`, { receipt_ids: ready.map((r) => r.id) });
      toast.success(`Tasdiq so'rovi yaratildi: ${r.data.description}`);
      setSel({}); setTick((t) => t + 1);
    } catch (e) { toast.error(e?.response?.data?.detail || "Xatolik"); }
  };

  if (!active) return <div className="p-8 text-muted-foreground">Kompaniyani tanlang.</div>;

  return (
    <div className="p-6 md:p-8 space-y-6" data-testid="receipts-page">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-heading text-3xl font-bold tracking-tight">Cheklar</h1>
          <p className="text-sm text-muted-foreground mt-1">my.soliq.uz → «Чеклар рўйхати» Excel faylini yuklang. AI MXIK va nom bo'yicha 1C mahsulotlariga moslaydi.</p>
        </div>
        <div className="flex gap-2">
          <input ref={fileRef} type="file" accept=".xlsx,.xlsm" className="hidden" onChange={upload} data-testid="soliq-file-input" />
          <Button onClick={() => fileRef.current?.click()} disabled={uploading} className="bg-emerald-600 hover:bg-emerald-700 rounded-sm" data-testid="soliq-upload-btn">
            {uploading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />} Soliq Excel yuklash
          </Button>
          <Button variant="outline" className="rounded-sm" disabled={ready.length === 0} onClick={sendTo1C} data-testid="send-to-1c-btn">
            <Send className="h-4 w-4 mr-2" /> 1C ga yozish ({ready.length})
          </Button>
        </div>
      </div>

      <ApprovalsPanel key={tick} companyId={active.id} onDone={load} />

      {rows.length === 0 ? (
        <div className="border-2 border-dashed rounded-sm p-12 text-center" data-testid="empty-receipts">
          <Receipt className="h-10 w-10 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">Hozircha cheklar yo'q</p>
          <p className="text-xs text-muted-foreground mt-2">Soliq Excel faylini yuklang yoki Telegram botga yuboring</p>
        </div>
      ) : (
        <div className="border rounded-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase tracking-widest">
              <tr>
                <th className="px-3 py-3 w-8"></th>
                <th className="text-left px-4 py-3">Raqam</th>
                <th className="text-left px-4 py-3">Sana</th>
                <th className="text-right px-4 py-3">Summa</th>
                <th className="text-left px-4 py-3">Moslik</th>
                <th className="text-left px-4 py-3">Holat</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-t hover:bg-muted/30 cursor-pointer" data-testid={`receipt-row-${r.id}`} onClick={() => setDetail(r.id)}>
                  <td className="px-3 py-3" onClick={(e) => e.stopPropagation()}>
                    <Checkbox checked={!!sel[r.id]} disabled={!(r.status === "matched" || r.status === "failed")}
                      onCheckedChange={(v) => setSel({ ...sel, [r.id]: !!v })} data-testid={`receipt-check-${r.id}`} />
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{r.receipt_number || r.external_id || "—"}</td>
                  <td className="px-4 py-3">{r.sale_date?.replace("T", " ").slice(0, 16) || "—"}</td>
                  <td className="px-4 py-3 text-right font-mono">{Number(r.total_amount || 0).toLocaleString()}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{r.items_matched}/{r.items_total} qator</td>
                  <td className="px-4 py-3">
                    <Badge className={`rounded-sm border ${STATUS_CLASSES[r.status] || ""}`}>{STATUS_UZ[r.status] || r.status}</Badge>
                    {r.status === "failed" && r.notes && <div className="text-xs text-red-600 mt-1 max-w-xs truncate">{r.notes}</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ReceiptDetailDialog receiptId={detail} companyId={active.id} onOpenChange={(o) => !o && setDetail(null)} onChanged={load} />
    </div>
  );
}
