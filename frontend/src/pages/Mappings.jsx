import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useCompany } from "@/context/CompanyContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { GitCompareArrows, Plus, Trash2, ArrowRight } from "lucide-react";
import { toast } from "sonner";

export default function Mappings() {
  const { active } = useCompany();
  const [rows, setRows] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ soliq_name: "", soliq_mxik: "", one_c_name: "", one_c_product_id: "" });

  const load = () => {
    if (!active) return;
    api.get(`/companies/${active.id}/mappings`).then((r) => setRows(r.data.mappings || []));
  };
  useEffect(() => { load(); }, [active]); // eslint-disable-line

  const save = async () => {
    if (!form.soliq_name.trim() || !form.one_c_name.trim()) return toast.error("Ikkala nom majburiy");
    try {
      await api.post("/mappings", { ...form, company_id: active.id });
      toast.success("Mapping saqlandi");
      setOpen(false); setForm({ soliq_name: "", soliq_mxik: "", one_c_name: "", one_c_product_id: "" });
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Xatolik"); }
  };

  const remove = async (id) => {
    if (!confirm("Mappingni o'chirish?")) return;
    await api.delete(`/mappings/${id}`);
    toast.success("O'chirildi"); load();
  };

  if (!active) return <div className="p-8 text-muted-foreground">Kompaniyani tanlang.</div>;

  return (
    <div className="p-6 md:p-8 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-3xl font-bold tracking-tight">Mahsulot Mappinglari</h1>
          <p className="text-sm text-muted-foreground mt-1">Soliq mahsulot ↔ 1C mahsulot bog'lanishi</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="add-mapping-btn" className="bg-emerald-600 hover:bg-emerald-700 rounded-sm">
              <Plus className="h-4 w-4 mr-2" /> Yangi mapping
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-background">
            <DialogHeader><DialogTitle>Mahsulot mappingi</DialogTitle></DialogHeader>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Soliq mahsulot nomi *</Label><Input data-testid="map-soliq-name" value={form.soliq_name} onChange={(e) => setForm({ ...form, soliq_name: e.target.value })} /></div>
              <div><Label>Soliq MXIK</Label><Input data-testid="map-soliq-mxik" value={form.soliq_mxik} onChange={(e) => setForm({ ...form, soliq_mxik: e.target.value })} /></div>
              <div><Label>1C mahsulot nomi *</Label><Input data-testid="map-onec-name" value={form.one_c_name} onChange={(e) => setForm({ ...form, one_c_name: e.target.value })} /></div>
              <div><Label>1C product ID</Label><Input data-testid="map-onec-id" value={form.one_c_product_id} onChange={(e) => setForm({ ...form, one_c_product_id: e.target.value })} /></div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(false)}>Bekor</Button>
              <Button onClick={save} data-testid="save-mapping-btn" className="bg-emerald-600 hover:bg-emerald-700">Saqlash</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {rows.length === 0 ? (
        <div className="border-2 border-dashed rounded-sm p-12 text-center">
          <GitCompareArrows className="h-10 w-10 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">Hali mappinglar yo'q</p>
        </div>
      ) : (
        <div className="space-y-2">
          {rows.map((m) => (
            <div key={m.id} className="border rounded-sm p-4 flex items-center gap-4 bg-background" data-testid={`mapping-row-${m.id}`}>
              <div className="flex-1">
                <div className="text-xs text-muted-foreground uppercase tracking-widest">Soliq</div>
                <div className="font-medium">{m.soliq_name}</div>
                {m.soliq_mxik && <div className="text-xs font-mono text-muted-foreground">MXIK: {m.soliq_mxik}</div>}
              </div>
              <ArrowRight className="h-5 w-5 text-emerald-600" />
              <div className="flex-1">
                <div className="text-xs text-muted-foreground uppercase tracking-widest">1C</div>
                <div className="font-medium">{m.one_c_name}</div>
              </div>
              <Button variant="ghost" size="icon" data-testid={`delete-mapping-${m.id}`} onClick={() => remove(m.id)}>
                <Trash2 className="h-4 w-4 text-red-600" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
