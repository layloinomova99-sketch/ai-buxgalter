import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useCompany } from "@/context/CompanyContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Package, Plus } from "lucide-react";
import { toast } from "sonner";

export default function Products() {
  const { active } = useCompany();
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", mxik: "", unit: "" });

  const load = () => {
    if (!active) return;
    api.get(`/companies/${active.id}/products`, { params: { q } })
       .then((r) => setRows(r.data.products || []));
  };
  useEffect(() => { load(); }, [active, q]); // eslint-disable-line

  const save = async () => {
    if (!form.name.trim()) return toast.error("Nom majburiy");
    try {
      await api.post("/products", { ...form, company_id: active.id });
      toast.success("Mahsulot qo'shildi");
      setOpen(false); setForm({ name: "", mxik: "", unit: "" });
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Xatolik"); }
  };

  if (!active) return <div className="p-8 text-muted-foreground">Kompaniyani tanlang.</div>;

  return (
    <div className="p-6 md:p-8 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-3xl font-bold tracking-tight">Mahsulotlar (1C katalog)</h1>
          <p className="text-sm text-muted-foreground mt-1">Kompaniya mahsulotlar katalogi</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="add-product-btn" className="bg-emerald-600 hover:bg-emerald-700 rounded-sm">
              <Plus className="h-4 w-4 mr-2" /> Yangi mahsulot
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-background">
            <DialogHeader><DialogTitle>Yangi mahsulot</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <div><Label>Nomi *</Label><Input data-testid="prod-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
              <div><Label>MXIK</Label><Input data-testid="prod-mxik" value={form.mxik} onChange={(e) => setForm({ ...form, mxik: e.target.value })} /></div>
              <div><Label>O'lchov birligi</Label><Input data-testid="prod-unit" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} /></div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(false)}>Bekor</Button>
              <Button onClick={save} data-testid="save-product-btn" className="bg-emerald-600 hover:bg-emerald-700">Saqlash</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Input placeholder="Nom bo'yicha qidiruv..." value={q} onChange={(e) => setQ(e.target.value)} className="max-w-md" data-testid="products-search" />

      {rows.length === 0 ? (
        <div className="border-2 border-dashed rounded-sm p-12 text-center">
          <Package className="h-10 w-10 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">Mahsulotlar yo'q. 1C sinxronlanmagan yoki qo'shilmagan.</p>
        </div>
      ) : (
        <div className="border rounded-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase tracking-widest">
              <tr><th className="text-left px-4 py-3">Nomi</th><th className="text-left px-4 py-3">MXIK</th><th className="text-left px-4 py-3">Birlik</th></tr>
            </thead>
            <tbody>
              {rows.map((p) => (
                <tr key={p.id} className="border-t hover:bg-muted/30">
                  <td className="px-4 py-3 font-medium">{p.name}</td>
                  <td className="px-4 py-3 font-mono text-xs">{p.mxik || "—"}</td>
                  <td className="px-4 py-3">{p.unit || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
