import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Loader2, Link2 } from "lucide-react";
import { toast } from "sonner";

const CONF = { high: "text-emerald-700", medium: "text-amber-700", low: "text-red-700" };

export function ReceiptDetailDialog({ receiptId, companyId, onOpenChange, onChanged }) {
  const [data, setData] = useState(null);
  const [pick, setPick] = useState(null);
  const [q, setQ] = useState("");
  const [products, setProducts] = useState([]);
  const [busy, setBusy] = useState(false);

  const load = () => receiptId && api.get(`/receipts/${receiptId}`).then((r) => setData(r.data));
  useEffect(() => { setData(null); setPick(null); load(); }, [receiptId]); // eslint-disable-line

  useEffect(() => {
    if (!pick) return;
    const t = setTimeout(() => api.get(`/companies/${companyId}/products`, { params: { q: q || undefined, limit: 15 } }).then((r) => setProducts(r.data.products || [])), 250);
    return () => clearTimeout(t);
  }, [q, pick, companyId]);

  const match = async (productId) => {
    setBusy(true);
    try {
      await api.post(`/receipt-items/${pick.id}/match`, { product_id: productId, save_mapping: true });
      toast.success("Bog'landi va mapping saqlandi"); setPick(null); load(); onChanged?.();
    } catch (e) { toast.error(e?.response?.data?.detail || "Xatolik"); }
    finally { setBusy(false); }
  };

  const r = data?.receipt;
  return (
    <Dialog open={!!receiptId} onOpenChange={onOpenChange}>
      <DialogContent className="bg-background max-w-3xl max-h-[85vh] overflow-y-auto" data-testid="receipt-detail-dialog">
        {!data ? <div className="p-6 text-muted-foreground">Yuklanmoqda...</div> : (
          <>
            <DialogHeader>
              <DialogTitle>Chek №{r.receipt_number} · {Number(r.total_amount).toLocaleString()} so'm</DialogTitle>
            </DialogHeader>
            <div className="flex gap-2 flex-wrap text-xs text-muted-foreground">
              <Badge variant="outline" className="rounded-sm">{r.status}</Badge>
              <span>{r.sale_date?.replace("T", " ")}</span>
              <span>naqd {Number(r.cash || 0).toLocaleString()} · karta {Number(r.card || 0).toLocaleString()}</span>
              <span className="font-mono">{r.external_id}</span>
              {r.one_c_ref && <span className="font-mono">1C: {r.one_c_ref}</span>}
            </div>
            <table className="w-full text-sm">
              <thead className="text-xs uppercase tracking-widest text-muted-foreground">
                <tr><th className="text-left py-2">Mahsulot (Soliq)</th><th className="text-right py-2">Miqdor</th><th className="text-right py-2">Summa</th><th className="text-left py-2 pl-4">1C mahsuloti</th><th></th></tr>
              </thead>
              <tbody>
                {data.items.map((it) => (
                  <tr key={it.id} className="border-t" data-testid={`item-row-${it.id}`}>
                    <td className="py-2">
                      <div>{it.name}</div>
                      {it.mxik && <div className="text-xs font-mono text-muted-foreground">MXIK {it.mxik}</div>}
                    </td>
                    <td className="py-2 text-right font-mono">{it.quantity}</td>
                    <td className="py-2 text-right font-mono">{Number(it.amount).toLocaleString()}</td>
                    <td className="py-2 pl-4">
                      <div className={it.matched_product_id ? "" : "text-muted-foreground italic"}>{it.matched_product_id ? it.matched_product_name : "bog'lanmagan"}</div>
                      <div className={`text-xs ${CONF[it.match_confidence] || ""}`}>{it.match_reason}</div>
                    </td>
                    <td className="py-2 text-right">
                      <Button size="sm" variant="outline" className="h-8 rounded-sm" onClick={() => { setPick(it); setQ(it.matched_product_name || it.name.split(" ")[0]); }} data-testid={`match-btn-${it.id}`}>
                        <Link2 className="h-3.5 w-3.5 mr-1" /> Bog'lash
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {pick && (
              <div className="border rounded-sm p-3 space-y-2 bg-muted/30" data-testid="match-picker">
                <div className="text-sm font-medium">"{pick.name}" uchun 1C mahsulotini tanlang</div>
                <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nom bo'yicha qidirish" data-testid="match-search" />
                <div className="max-h-48 overflow-y-auto divide-y">
                  {products.length === 0 && <div className="text-sm text-muted-foreground py-2">Topilmadi. Avval 1C mahsulotlarini sinxronlang.</div>}
                  {products.map((p) => (
                    <button key={p.id} disabled={busy} onClick={() => match(p.id)} data-testid={`pick-product-${p.id}`}
                      className="w-full text-left text-sm py-2 px-2 hover:bg-accent flex justify-between">
                      <span>{p.name}</span><span className="text-xs font-mono text-muted-foreground">{p.mxik || ""}</span>
                    </button>
                  ))}
                </div>
                {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              </div>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
