import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useCompany } from "@/context/CompanyContext";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { ScrollText, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";

const CATEGORIES = [
  "company_rules", "accounting_rules", "soliq_rules", "one_c_rules",
  "product_mapping_rules", "mxik_rules", "receipt_rules",
  "marketplace_rules", "integration_rules", "creator_instructions",
];

export default function Rules() {
  const { active } = useCompany();
  const { user } = useAuth();
  const isCreator = user?.role === "creator";
  const [rows, setRows] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ category: "company_rules", instruction: "", priority: 50, scope: "company" });

  const load = () => {
    const params = {};
    if (active) params.company_id = active.id;
    api.get("/rules", { params }).then((r) => setRows(r.data.rules || []));
  };
  useEffect(() => { load(); }, [active]); // eslint-disable-line

  const save = async () => {
    if (!form.instruction.trim()) return toast.error("Qoida matni majburiy");
    try {
      await api.post("/rules", {
        category: form.category,
        instruction: form.instruction,
        priority: Number(form.priority) || 50,
        company_id: form.scope === "company" && active ? active.id : null,
        status: "active",
      });
      toast.success("Qoida saqlandi");
      setOpen(false); setForm({ category: "company_rules", instruction: "", priority: 50, scope: "company" });
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Xatolik"); }
  };

  const remove = async (id) => {
    if (!confirm("Qoidani o'chirish?")) return;
    await api.delete(`/rules/${id}`); toast.success("O'chirildi"); load();
  };

  return (
    <div className="p-6 md:p-8 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-3xl font-bold tracking-tight">AI Qoidalari</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {isCreator ? "Creator sifatida AI'ni bu qoidalar orqali o'rgatasiz" : "Kompaniya + global qoidalar (faqat o'qish)"}
          </p>
        </div>
        {isCreator && (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button data-testid="add-rule-btn" className="bg-emerald-600 hover:bg-emerald-700 rounded-sm">
                <Plus className="h-4 w-4 mr-2" /> Qoida qo'shish
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-background max-w-lg">
              <DialogHeader><DialogTitle>Yangi qoida</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <div>
                  <Label>Kategoriya</Label>
                  <Select value={form.category} onValueChange={(v) => setForm({ ...form, category: v })}>
                    <SelectTrigger data-testid="rule-category-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Ko'lam</Label>
                  <Select value={form.scope} onValueChange={(v) => setForm({ ...form, scope: v })}>
                    <SelectTrigger data-testid="rule-scope-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="company" disabled={!active}>Kompaniya ({active?.name || "yo'q"})</SelectItem>
                      <SelectItem value="global">Global (barcha)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Qoida matni</Label>
                  <Textarea data-testid="rule-instruction" rows={5} value={form.instruction}
                    onChange={(e) => setForm({ ...form, instruction: e.target.value })}
                    placeholder="Masalan: Yandex orqali kelgan cheklarni marketplace savdosi sifatida ajrat." />
                </div>
                <div>
                  <Label>Ustuvorlik (1-100)</Label>
                  <Input type="number" data-testid="rule-priority" value={form.priority}
                    onChange={(e) => setForm({ ...form, priority: e.target.value })} />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setOpen(false)}>Bekor</Button>
                <Button onClick={save} data-testid="save-rule-btn" className="bg-emerald-600 hover:bg-emerald-700">Saqlash</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {rows.length === 0 ? (
        <div className="border-2 border-dashed rounded-sm p-12 text-center">
          <ScrollText className="h-10 w-10 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">Hali qoidalar yo'q</p>
        </div>
      ) : (
        <div className="space-y-2">
          {rows.map((r) => (
            <div key={r.id} className="border rounded-sm p-4 bg-background" data-testid={`rule-row-${r.id}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline" className="rounded-sm font-mono text-xs">{r.category}</Badge>
                    <Badge variant="outline" className="rounded-sm">{r.company_id ? "Kompaniya" : "Global"}</Badge>
                    <span className="text-xs text-muted-foreground">P: {r.priority} · v{r.version}</span>
                  </div>
                  <p className="text-sm leading-relaxed">{r.instruction}</p>
                </div>
                {isCreator && (
                  <Button variant="ghost" size="icon" data-testid={`delete-rule-${r.id}`} onClick={() => remove(r.id)}>
                    <Trash2 className="h-4 w-4 text-red-600" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
