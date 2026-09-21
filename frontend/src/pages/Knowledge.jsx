import React, { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useCompany } from "@/context/CompanyContext";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { BookOpen, Upload, Trash2, Send, FileText, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";

const CATEGORIES = [
  "company_rules", "accounting_rules", "soliq_rules", "one_c_rules",
  "product_mapping_rules", "mxik_rules", "receipt_rules",
  "marketplace_rules", "integration_rules", "creator_instructions",
];

const CATEGORY_LABELS = {
  company_rules: "Kompaniya qoidalari",
  accounting_rules: "Buxgalteriya qoidalari",
  soliq_rules: "Soliq qoidalari",
  one_c_rules: "1C qoidalari",
  product_mapping_rules: "Mahsulot mapping qoidalari",
  mxik_rules: "MXIK qoidalari",
  receipt_rules: "Chek qoidalari",
  marketplace_rules: "Marketplace qoidalari",
  integration_rules: "Integratsiya qoidalari",
  creator_instructions: "Creator ko'rsatmalari",
};

const CATEGORY_HINTS = {
  company_rules: "Kompaniya ma'lumotlari, INN, faoliyat turi va boshqa umumiy tafsilotlar",
  accounting_rules: "Hisob-kitob, hujjatlar tartibi, buxgalteriya siyosati",
  soliq_rules: "Soliq tizimi bilan ishlash tartibi, cheklar, e-faktura",
  one_c_rules: "1C bilan integratsiya, hujjatlar nomlari, hisob ustunlari",
  product_mapping_rules: "Soliq mahsulotlarini 1C mahsulotlariga bog'lash qoidalari",
  mxik_rules: "MXIK kodlari bo'yicha qoidalar",
  receipt_rules: "Chek turlarini aniqlash va tahlil qilish",
  marketplace_rules: "Yandex, Uzum va boshqa marketplace cheklari",
  integration_rules: "Tashqi tizimlar bilan bog'lanish (API, ERI, EIMZO)",
  creator_instructions: "AI uchun umumiy ko'rsatmalar va ish tartibi",
};

const StatusIcon = ({ status }) => {
  if (status === "ready") return <CheckCircle2 className="h-4 w-4 text-emerald-600" />;
  if (status === "failed") return <XCircle className="h-4 w-4 text-red-600" />;
  return <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />;
};

export default function Knowledge() {
  const { active } = useCompany();
  const [docs, setDocs] = useState([]);
  const [tg, setTg] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [note, setNote] = useState("");
  const [detail, setDetail] = useState(null);
  const [category, setCategory] = useState("");
  const fileRef = useRef(null);

  const load = () => {
    api.get("/knowledge").then((r) => setDocs(r.data.documents || []));
    api.get("/telegram/status").then((r) => setTg(r.data)).catch(() => {});
  };
  useEffect(load, []);

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    if (active) fd.append("company_id", active.id);
    const fullNote = category ? `Kategoriya: ${category}${note ? ". " + note : ""}` : note;
    if (fullNote) fd.append("note", fullNote);
    try {
      const r = await api.post("/knowledge/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      if (r.data.status === "ready") toast.success(`${r.data.rules_count} ta qoida ajratildi`);
      else toast.error(r.data.error || "Tahlil qilinmadi");
      setNote("");
      load();
    } catch (err) { toast.error(err?.response?.data?.detail || "Xatolik"); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
  };

  const remove = async (id) => {
    if (!confirm("Hujjat va undan olingan qoidalar o'chiriladi. Davom etasizmi?")) return;
    await api.delete(`/knowledge/${id}`); toast.success("O'chirildi"); load();
  };

  const openDetail = async (id) => {
    const r = await api.get(`/knowledge/${id}`); setDetail(r.data);
  };

  return (
    <div className="p-6 md:p-8 space-y-6" data-testid="knowledge-page">
      <div>
        <h1 className="font-heading text-3xl font-bold tracking-tight">Bilim bazasi</h1>
        <p className="text-sm text-muted-foreground mt-1">AI'ni fayllar orqali o'rgatish — Telegram bot yoki shu yerdan yuklang</p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="border rounded-sm p-5 bg-background space-y-3" data-testid="telegram-card">
          <div className="flex items-center gap-2 font-medium"><Send className="h-4 w-4 text-sky-600" /> Telegram bot</div>
          {tg ? (
            <>
              <p className="text-sm text-muted-foreground">
                {tg.bot_configured ? (
                  <>Bot: <a className="text-emerald-700 underline" href={`https://t.me/${tg.bot_username}`} target="_blank" rel="noreferrer" data-testid="telegram-bot-link">@{tg.bot_username}</a></>
                ) : "Bot token sozlanmagan"}
              </p>
              <Badge variant="outline" className="rounded-sm" data-testid="telegram-link-status">
                {tg.linked ? `Bog'langan: @${tg.telegram_username || "—"}` : "Hisob bog'lanmagan"}
              </Badge>
              {!tg.linked && (
                <p className="text-xs text-muted-foreground">Botga <code>/login email parol</code> yuboring. Faqat Creator hisobi bog'lanadi.</p>
              )}
              <p className="text-xs text-muted-foreground">Botga fayl yuboring yoki oddiy matnda tushuntiring — AI qoidalarni shu yerda ko'rsatadi.</p>
            </>
          ) : <p className="text-sm text-muted-foreground">Yuklanmoqda...</p>}
        </div>

        <div className="border rounded-sm p-5 bg-background space-y-3" data-testid="upload-card">
          <div className="flex items-center gap-2 font-medium"><Upload className="h-4 w-4 text-emerald-600" /> Web orqali yuklash</div>
          <select
            data-testid="knowledge-category"
            className="flex h-10 w-full rounded-sm border border-input bg-background px-3 py-2 text-sm"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">Kategoriya (ixtiyoriy)</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
            ))}
          </select>
          {category && (
            <p className="text-xs text-muted-foreground" data-testid="category-hint">{CATEGORY_HINTS[category]}</p>
          )}
          <Input data-testid="knowledge-note" placeholder="Izoh (ixtiyoriy): bu fayl nima haqida?" value={note} onChange={(e) => setNote(e.target.value)} />
          <input ref={fileRef} type="file" className="hidden" onChange={upload} data-testid="knowledge-file-input"
            accept=".py,.txt,.md,.json,.csv,.pdf,.docx,.xlsx,.jpg,.jpeg,.png,.webp,.xml,.bsl" />
          <Button data-testid="knowledge-upload-btn" disabled={uploading} onClick={() => fileRef.current?.click()} className="bg-emerald-600 hover:bg-emerald-700 rounded-sm">
            {uploading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> AI tahlil qilmoqda...</> : <><Upload className="h-4 w-4 mr-2" /> Fayl tanlash</>}
          </Button>
          <p className="text-xs text-muted-foreground">{active ? `Kompaniya: ${active.name}` : "Global (kompaniyasiz)"} · .py .pdf .docx .xlsx .txt .json, rasm · 20 MB gacha</p>
        </div>
      </div>

      {docs.length === 0 ? (
        <div className="border-2 border-dashed rounded-sm p-12 text-center" data-testid="knowledge-empty">
          <BookOpen className="h-10 w-10 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">Hali fayl yuklanmagan</p>
        </div>
      ) : (
        <div className="space-y-2">
          {docs.map((d) => (
            <div key={d.id} className="border rounded-sm p-4 bg-background flex items-start gap-4" data-testid={`knowledge-row-${d.id}`}>
              <FileText className="h-5 w-5 mt-0.5 text-muted-foreground shrink-0" />
              <div className="flex-1 min-w-0 cursor-pointer" onClick={() => openDetail(d.id)}>
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <StatusIcon status={d.status} />
                  <span className="font-medium truncate">{d.title || d.filename}</span>
                  <Badge variant="outline" className="rounded-sm text-xs">{d.source}</Badge>
                  <Badge variant="outline" className="rounded-sm text-xs">{d.rules_count} qoida</Badge>
                  <span className="text-xs text-muted-foreground">{d.filename}</span>
                </div>
                <p className="text-sm text-muted-foreground line-clamp-2">{d.summary}</p>
              </div>
              <Button variant="ghost" size="icon" data-testid={`delete-knowledge-${d.id}`} onClick={() => remove(d.id)}>
                <Trash2 className="h-4 w-4 text-red-600" />
              </Button>
            </div>
          ))}
        </div>
      )}

      <Dialog open={!!detail} onOpenChange={(o) => !o && setDetail(null)}>
        <DialogContent className="bg-background max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="knowledge-detail-dialog">
          {detail && (
            <>
              <DialogHeader><DialogTitle>{detail.title || detail.filename}</DialogTitle></DialogHeader>
              <p className="text-sm leading-relaxed">{detail.summary}</p>
              {detail.key_facts?.length > 0 && (
                <div>
                  <div className="text-xs uppercase tracking-widest text-muted-foreground mb-2">Asosiy faktlar</div>
                  <ul className="list-disc pl-5 text-sm space-y-1">{detail.key_facts.map((f, i) => <li key={i}>{f}</li>)}</ul>
                </div>
              )}
              <div>
                <div className="text-xs uppercase tracking-widest text-muted-foreground mb-2">Ajratilgan qoidalar ({detail.rules?.length || 0})</div>
                <div className="space-y-2">
                  {(detail.rules || []).map((r) => (
                    <div key={r.id} className="border rounded-sm p-3 text-sm">
                      <Badge variant="outline" className="rounded-sm font-mono text-xs mr-2">{r.category}</Badge>
                      <span className="text-xs text-muted-foreground">P: {r.priority}</span>
                      <p className="mt-1">{r.instruction}</p>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
