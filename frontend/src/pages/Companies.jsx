import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useCompany } from "@/context/CompanyContext";
import { AddCompanyDialog } from "@/components/app/AddCompanyDialog";
import { Building2, Trash2, Plug } from "lucide-react";
import { OneCDialog } from "@/components/app/OneCDialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";

export default function Companies() {
  const { companies, refresh } = useCompany();
  const [oneC, setOneC] = useState(null);

  const remove = async (id) => {
    if (!confirm("Kompaniya va uning barcha ma'lumotlari o'chiriladi. Davom etamizmi?")) return;
    try {
      await api.delete(`/companies/${id}`);
      toast.success("O'chirildi");
      refresh();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Xatolik");
    }
  };

  return (
    <div className="p-6 md:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-3xl font-bold tracking-tight">Kompaniyalar</h1>
          <p className="text-sm text-muted-foreground mt-1">Limit: 10 ta kompaniya. Har biri qat'iy izolyatsiyalangan.</p>
        </div>
        <AddCompanyDialog />
      </div>

      {companies.length === 0 ? (
        <div className="border-2 border-dashed rounded-sm p-12 text-center" data-testid="empty-companies">
          <Building2 className="h-10 w-10 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">Kompaniya qo'shilmagan</p>
        </div>
      ) : (
        <div className="border rounded-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase tracking-widest">
              <tr>
                <th className="text-left px-4 py-3">Nomi</th>
                <th className="text-left px-4 py-3">INN</th>
                <th className="text-left px-4 py-3">ERI</th>
                <th className="text-left px-4 py-3">1C</th>
                <th className="text-left px-4 py-3">Soliq</th>
                <th className="text-right px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {companies.map((c) => (
                <tr key={c.id} className="border-t hover:bg-muted/30" data-testid={`company-row-${c.id}`}>
                  <td className="px-4 py-3 font-medium">{c.name}</td>
                  <td className="px-4 py-3 font-mono text-xs">{c.inn || "—"}</td>
                  <td className="px-4 py-3"><Badge variant="outline" className="rounded-sm">{c.eri_status}</Badge></td>
                  <td className="px-4 py-3"><Badge variant="outline" className="rounded-sm">{c.one_c_status}</Badge></td>
                  <td className="px-4 py-3"><Badge variant="outline" className="rounded-sm">{c.soliq_status}</Badge></td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <Button variant="outline" size="sm" className="rounded-sm mr-2" data-testid={`one-c-btn-${c.id}`} onClick={() => setOneC(c)}>
                      <Plug className="h-3.5 w-3.5 mr-1" /> 1C
                    </Button>
                    <Button variant="ghost" size="icon" data-testid={`delete-company-${c.id}`} onClick={() => remove(c.id)}>
                      <Trash2 className="h-4 w-4 text-red-600" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <OneCDialog company={oneC} open={!!oneC} onOpenChange={(o) => !o && setOneC(null)} onChanged={refresh} />
    </div>
  );
}
