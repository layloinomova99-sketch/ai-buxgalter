import React, { useEffect, useState } from "react";
import { useCompany } from "@/context/CompanyContext";
import { AddCompanyDialog } from "@/components/app/AddCompanyDialog";
import { Building2, Receipt, Package, GitCompareArrows, ScrollText, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

const MetricCard = ({ label, value, icon: Icon, sub }) => (
  <div className="border rounded-sm p-5 bg-background hover:shadow-sm transition-shadow duration-150" data-testid={`metric-${label}`}>
    <div className="flex items-center justify-between mb-4">
      <span className="text-xs uppercase tracking-widest text-muted-foreground font-medium">{label}</span>
      <Icon className="h-4 w-4 text-emerald-600" />
    </div>
    <div className="font-heading text-3xl font-bold tracking-tight">{value ?? "—"}</div>
    {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
  </div>
);

export default function Dashboard() {
  const { active, companies } = useCompany();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (!active) { setStats(null); return; }
    api.get(`/companies/${active.id}/stats`).then((r) => setStats(r.data)).catch(() => setStats(null));
  }, [active]);

  if (companies.length === 0) {
    return (
      <div className="p-8 md:p-16 flex items-center justify-center min-h-[80vh]" data-testid="empty-state-dashboard">
        <div className="max-w-lg text-center border-2 border-dashed rounded-sm p-16 bg-background">
          <div className="mx-auto w-16 h-16 rounded-sm bg-emerald-50 dark:bg-emerald-950 flex items-center justify-center mb-6">
            <Building2 className="h-8 w-8 text-emerald-700 dark:text-emerald-400" />
          </div>
          <h2 className="font-heading text-2xl font-bold tracking-tight mb-2">Xush kelibsiz!</h2>
          <p className="text-sm text-muted-foreground mb-6">
            Hozircha bironta kompaniya qo'shilmagan. Ishni boshlash uchun avval o'z kompaniyangizni qo'shing.
            Har bir foydalanuvchi faqat o'zi qo'shgan yoki ruxsat berilgan kompaniyalarni ko'radi.
          </p>
          <AddCompanyDialog />
        </div>
      </div>
    );
  }

  if (!active) {
    return <div className="p-8 text-muted-foreground">Yuqori paneldan kompaniyani tanlang.</div>;
  }

  return (
    <div className="p-6 md:p-8 space-y-6">
      <div>
        <div className="text-xs uppercase tracking-widest text-muted-foreground font-medium mb-1">Kompaniya</div>
        <h1 className="font-heading text-3xl font-bold tracking-tight">{active.name}</h1>
        <div className="flex flex-wrap gap-2 mt-2 text-xs">
          {active.inn && <Badge variant="outline" className="rounded-sm font-mono">INN: {active.inn}</Badge>}
          <Badge variant="outline" className="rounded-sm">ERI: {active.eri_status}</Badge>
          <Badge variant="outline" className="rounded-sm">1C: {active.one_c_status}</Badge>
          <Badge variant="outline" className="rounded-sm">Soliq: {active.soliq_status}</Badge>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard label="Cheklar" value={stats?.receipts_total ?? 0} icon={Receipt} />
        <MetricCard label="Tekshirish kerak" value={stats?.receipts_needs_review ?? 0} icon={AlertTriangle} />
        <MetricCard label="1C ga o'tkazilgan" value={stats?.receipts_imported ?? 0} icon={Receipt} />
        <MetricCard label="Mahsulotlar" value={stats?.products_total ?? 0} icon={Package} />
        <MetricCard label="Mappinglar" value={stats?.mappings_total ?? 0} icon={GitCompareArrows} />
        <MetricCard label="Qoidalar" value={stats?.rules_total ?? 0} icon={ScrollText} />
      </div>

      <div className="border rounded-sm p-6 bg-muted/30">
        <h3 className="font-heading text-lg font-semibold mb-2">Boshlash uchun</h3>
        <ul className="text-sm text-muted-foreground space-y-1 list-disc pl-5">
          <li>Kompaniya sahifasidan ERI, 1C va Soliq ulanish sozlamalarini kiriting</li>
          <li>Mahsulotlar sahifasida 1C katalogini qo'shing yoki keyinroq sinxronlashtiring</li>
          <li>AI Yordamchi bilan gaplashib boshlang — u sizga kerakli tool'larni ishlatadi</li>
          <li>Creator qoidalarni tabiiy tilda o'rgatishi mumkin (Qoidalar sahifasi)</li>
        </ul>
      </div>
    </div>
  );
}
