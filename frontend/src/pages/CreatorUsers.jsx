import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";

export default function CreatorUsers() {
  const [rows, setRows] = useState([]);
  const load = () => api.get("/creator/users").then((r) => setRows(r.data.users || []));
  useEffect(() => { load(); }, []);

  const toggle = async (id, field, value) => {
    try {
      await api.patch(`/creator/users/${id}`, { [field]: value });
      toast.success("Yangilandi"); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Xatolik"); }
  };

  return (
    <div className="p-6 md:p-8 space-y-6">
      <div>
        <h1 className="font-heading text-3xl font-bold tracking-tight">Foydalanuvchilar</h1>
        <p className="text-sm text-muted-foreground mt-1">Access berish/olib qo'yish. Parollar hech qachon ko'rinmaydi.</p>
      </div>
      <div className="border rounded-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-xs uppercase tracking-widest">
            <tr>
              <th className="text-left px-4 py-3">Ism</th>
              <th className="text-left px-4 py-3">Email</th>
              <th className="text-left px-4 py-3">Rol</th>
              <th className="text-left px-4 py-3">Kompaniyalar</th>
              <th className="text-left px-4 py-3">Faol</th>
              <th className="text-left px-4 py-3">Access</th>
              <th className="text-left px-4 py-3">To'lov</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((u) => (
              <tr key={u.id} className="border-t" data-testid={`user-row-${u.id}`}>
                <td className="px-4 py-3 font-medium">{u.full_name}</td>
                <td className="px-4 py-3 font-mono text-xs">{u.email}</td>
                <td className="px-4 py-3"><Badge variant="outline" className="rounded-sm">{u.role}</Badge></td>
                <td className="px-4 py-3">{u.companies_count}</td>
                <td className="px-4 py-3">
                  <Switch checked={!!u.active} onCheckedChange={(v) => toggle(u.id, "active", v)}
                    data-testid={`toggle-active-${u.id}`} />
                </td>
                <td className="px-4 py-3">
                  <Switch checked={!!u.access_granted} onCheckedChange={(v) => toggle(u.id, "access_granted", v)}
                    data-testid={`toggle-access-${u.id}`} />
                </td>
                <td className="px-4 py-3">
                  <Badge variant="outline" className="rounded-sm">{u.payment_status}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
