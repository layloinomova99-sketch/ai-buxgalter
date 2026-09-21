import React, { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useCompany } from "@/context/CompanyContext";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Sparkles, Send, Wrench, User } from "lucide-react";
import { toast } from "sonner";

export default function AIChat() {
  const { active } = useCompany();
  const [convId, setConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text, id: `tmp-${Date.now()}` }]);
    setSending(true);
    try {
      const { data } = await api.post("/ai/chat", {
        conversation_id: convId,
        company_id: active?.id || null,
        message: text,
      });
      setConvId(data.conversation_id);
      setMessages((m) => [...m, { role: "assistant", content: data.content, tool_calls: data.tool_trace, id: `a-${Date.now()}` }]);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "AI xatosi");
    } finally { setSending(false); }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      <div className="border-b px-6 py-4 flex items-center gap-3 bg-background/80 backdrop-blur-md">
        <Sparkles className="h-5 w-5 text-emerald-600" />
        <div>
          <h1 className="font-heading text-xl font-bold tracking-tight">AI Yordamchi</h1>
          <p className="text-xs text-muted-foreground">
            {active ? `Kontekst: ${active.name}` : "Kompaniya tanlanmagan — umumiy savollar"}
          </p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4 max-w-3xl w-full mx-auto" data-testid="ai-chat-messages">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground py-16 space-y-2">
            <Sparkles className="h-8 w-8 mx-auto text-emerald-600" />
            <p className="font-heading text-lg">AI'ga savol bering</p>
            <p className="text-sm">Masalan: "Bugun nechta chek keldi?" yoki "Mappingsiz mahsulotlarni ko'rsat"</p>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
            {m.role !== "user" && (
              <div className="w-8 h-8 rounded-sm bg-emerald-600 text-white flex items-center justify-center shrink-0">
                <Sparkles className="h-4 w-4" />
              </div>
            )}
            <div className={`max-w-[80%] space-y-2 ${m.role === "user" ? "text-right" : ""}`}>
              <div className={`inline-block px-4 py-3 rounded-sm text-sm leading-relaxed whitespace-pre-wrap ${
                m.role === "user" ? "bg-emerald-600 text-white" : "bg-muted"
              }`}>
                {m.content || <span className="italic opacity-60">(bo'sh javob)</span>}
              </div>
              {m.tool_calls?.length > 0 && (
                <details className="text-xs text-muted-foreground text-left">
                  <summary className="cursor-pointer flex items-center gap-1 hover:text-foreground">
                    <Wrench className="h-3 w-3" /> {m.tool_calls.length} ta tool chaqirildi
                  </summary>
                  <div className="mt-2 space-y-1 font-mono">
                    {m.tool_calls.map((t, i) => (
                      <div key={i} className="border rounded-sm p-2 bg-background">
                        <div className="text-emerald-600">→ {t.tool}({JSON.stringify(t.arguments)})</div>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
            {m.role === "user" && (
              <div className="w-8 h-8 rounded-sm bg-foreground text-background flex items-center justify-center shrink-0">
                <User className="h-4 w-4" />
              </div>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <div className="border-t p-4 bg-background">
        <div className="max-w-3xl mx-auto flex gap-2">
          <Textarea
            data-testid="ai-chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder="Savolingizni yozing... (Enter — yuborish, Shift+Enter — yangi qator)"
            rows={2}
            className="flex-1 resize-none"
          />
          <Button onClick={send} disabled={sending || !input.trim()} data-testid="ai-chat-send-btn"
            className="bg-emerald-600 hover:bg-emerald-700 rounded-sm">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
