import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Plug, Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";

export function OneCDialog({ company, open, onOpenChange, onChanged }) {
  const [conn, setConn] = useState(null);
  const [form, setForm] = useState({ base_url: "", username: "", password: "" });
  const [busy, setBusy] = useState("");

  useEffect(() => {
    if (!open || !company) return;
    api.get(`/companies/${company.id}/one-c`).then((r) => {
      setConn(r.data);
      setForm({ base_url: r.data.base_url || "", username: r.data.username || "", password: "" });
    });
  }, [open, company]);

  const save = async () => {
    if (!form.base_url.trim()) return toast.error("1C URL majburiy");
    setBusy("save");
    try {
      const r = await api.put(`/companies/${company.id}/one-c`, { ...form, password: form.password || null, auth_mode: "basic" });
      setConn(r.data); toast.success("Saqlandi");
    } catch (e) { toast.error(e?.response?.data?.detail || "Xatolik"); }
    finally { setBusy(""); }
  };

  const test = async () => {
    setBusy("test");
    try {
      const r = await api.post(`/companies/${company.id}/one-c/test`);
      if (r.data.ok) toast.success(`Ulandi: ${r.data.entities} ta obyekt${r.data.summary?.check_document ? `, chek hujjati: ${r.data.summary.check_document}` : ""}`);
      else toast.error(r.data.reason || "Ulanmadi");
      const c = await api.get(`/companies/${company.id}/one-c`); setConn(c.data); onChanged?.();
    } catch (e) { toast.error(e?.response?.data?.detail || "Xatolik"); }
    finally { setBusy(""); }
  };

  const sync = async () => {
    setBusy("sync");
    try {
      const r = await api.post(`/companies/${company.id}/one-c/sync-products`);
      toast.success(`${r.data.synced} ta mahsulot sinxronlandi`);
      const c = await api.get(`/companies/${company.id}/one-c`); setConn(c.data); onChanged?.();
    } catch (e) { toast.error(e?.response?.data?.detail || "Xatolik"); }
    finally { setBusy(""); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-background max-w-lg" data-testid="one-c-dialog">
        <DialogHeader><DialogTitle className="flex items-center gap-2"><Plug className="h-4 w-4" /> 1C ulanish — {company?.name}</DialogTitle></DialogHeader>
        {conn && (
          <div className="flex items-center gap-2 text-sm flex-wrap">
            <Badge variant="outline" className="rounded-sm" data-testid="one-c-status">{conn.status}</Badge>
            {conn.entities != null && <span className="text-muted-foreground">{conn.entities} obyekt</span>}
            {conn.check_document && <span className="text-muted-foreground font-mono text-xs">{conn.check_document}</span>}
            {conn.products_synced != null && <span className="text-muted-foreground">{conn.products_synced} mahsulot</span>}
            {conn.last_error && <p className="text-xs text-red-600 w-full" data-testid="one-c-error">{conn.last_error}</p>}
          </div>
        )}
        <div className="space-y-3">
          <div>
            <Label>OData URL (Clobus ilova havolasi ham bo'ladi)</Label>
            <Input data-testid="one-c-url" value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })}
              placeholder="https://clobus.uz/a/acc320/76202/ yoki .../odata/standard.odata" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Login</Label>
              <Input data-testid="one-c-username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
            </div>
            <div>
              <Label>Parol {conn?.has_password && <span className="text-xs text-muted-foreground">(saqlangan)</span>}</Label>
              <Input data-testid="one-c-password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder={conn?.has_password ? "O'zgartirish uchun yozing" : ""} />
            </div>
          </div>
          <p className="text-xs text-muted-foreground">Parol shifrlangan holda saqlanadi. Ulanish tekshirilgach chek hujjati tuzilmasi avtomatik aniqlanadi.</p>
        </div>
        <DialogFooter className="gap-2 flex-wrap">
          <Button variant="outline" onClick={sync} disabled={!!busy || conn?.status !== "connected"} data-testid="one-c-sync-btn">
            {busy === "sync" ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />} Mahsulotlarni sinxronlash
          </Button>
          <Button variant="outline" onClick={test} disabled={!!busy || !conn?.configured} data-testid="one-c-test-btn">
            {busy === "test" && <Loader2 className="h-4 w-4 animate-spin mr-2" />} Ulanishni tekshirish
          </Button>
          <Button onClick={save} disabled={!!busy} className="bg-emerald-600 hover:bg-emerald-700" data-testid="one-c-save-btn">
            {busy === "save" && <Loader2 className="h-4 w-4 animate-spin mr-2" />} Saqlash
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
