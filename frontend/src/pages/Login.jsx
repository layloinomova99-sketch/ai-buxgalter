import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Sparkles } from "lucide-react";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(form.email, form.password);
      toast.success("Xush kelibsiz!");
      navigate("/");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Kirishda xatolik");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen grid md:grid-cols-2">
      <div className="hidden md:flex flex-col justify-between p-12 bg-emerald-950 text-white">
        <div className="flex items-center gap-2 font-heading text-xl font-bold tracking-tight">
          <Sparkles className="h-5 w-5" /> AI BUXGALTER
        </div>
        <div className="space-y-4">
          <h1 className="font-heading text-4xl font-bold tracking-tight leading-tight">
            O'zbekiston uchun aqlli<br />buxgalteriya platformasi
          </h1>
          <p className="text-emerald-100/80 max-w-md">
            Soliq, 1C, ERI/EIMZO, Marketplace cheklari — bir joyda.
            AI Creator bergan qoidalarga asosan avtomatlashtiradi.
          </p>
        </div>
        <div className="text-xs text-emerald-200/70">v0.1 · Web + Telegram · Uzbek</div>
      </div>

      <div className="flex items-center justify-center p-8">
        <form onSubmit={submit} className="w-full max-w-sm space-y-6" data-testid="login-form">
          <div>
            <h2 className="font-heading text-2xl font-semibold tracking-tight">Tizimga kirish</h2>
            <p className="text-sm text-muted-foreground mt-1">Email va parolingizni kiriting</p>
          </div>
          <div className="space-y-3">
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" required data-testid="login-email"
                value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </div>
            <div>
              <Label htmlFor="password">Parol</Label>
              <Input id="password" type="password" required data-testid="login-password"
                value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </div>
          </div>
          <Button type="submit" disabled={loading} data-testid="login-submit-btn"
            className="w-full bg-emerald-600 hover:bg-emerald-700 rounded-sm">
            {loading ? "Kirilmoqda..." : "Kirish"}
          </Button>
          <div className="text-sm text-center text-muted-foreground">
            Hisobingiz yo'qmi?{" "}
            <Link to="/register" className="text-emerald-700 hover:underline" data-testid="goto-register-link">
              Ro'yxatdan o'ting
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
