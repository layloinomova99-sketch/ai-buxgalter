import React, { useState } from "react";
import { Building2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useCompany } from "@/context/CompanyContext";

export function AddCompanyDialog({ trigger }) {
  const { refresh, setActive } = useCompany();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", inn: "", address: "", director: "" });
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!form.name.trim()) { toast.error("Kompaniya nomi majburiy"); return; }
    setSaving(true);
    try {
      const { data } = await api.post("/companies", form);
      toast.success("Kompaniya qo'shildi");
      await refresh();
      setActive(data.id);
      setOpen(false);
      setForm({ name: "", inn: "", address: "", director: "" });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Xatolik yuz berdi");
    } finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || <Button data-testid="add-company-btn" className="bg-emerald-600 hover:bg-emerald-700 rounded-sm">
          <Building2 className="h-4 w-4 mr-2" /> Kompaniya qo'shish
        </Button>}
      </DialogTrigger>
      <DialogContent className="bg-background rounded-sm">
        <DialogHeader>
          <DialogTitle className="font-heading">Yangi kompaniya qo'shish</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label htmlFor="c-name">Nomi *</Label>
            <Input id="c-name" data-testid="new-company-name" value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Masalan: ABC MCHJ" />
          </div>
          <div>
            <Label htmlFor="c-inn">INN / STIR</Label>
            <Input id="c-inn" data-testid="new-company-inn" value={form.inn}
              onChange={(e) => setForm({ ...form, inn: e.target.value })} placeholder="123456789" />
          </div>
          <div>
            <Label htmlFor="c-addr">Manzil</Label>
            <Input id="c-addr" data-testid="new-company-address" value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })} />
          </div>
          <div>
            <Label htmlFor="c-dir">Direktor</Label>
            <Input id="c-dir" data-testid="new-company-director" value={form.director}
              onChange={(e) => setForm({ ...form, director: e.target.value })} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} data-testid="cancel-company-btn">Bekor qilish</Button>
          <Button onClick={submit} disabled={saving} data-testid="save-company-btn"
            className="bg-emerald-600 hover:bg-emerald-700">
            {saving ? "Saqlanmoqda..." : "Saqlash"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
