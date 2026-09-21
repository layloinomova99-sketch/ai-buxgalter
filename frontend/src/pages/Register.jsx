import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", password: "" });
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (form.password.length < 8) { toast.error("Parol kamida 8 belgi bo'lsin"); return; }
    setLoading(true);
    try {
      await register(form);
      toast.success("Ro'yxatdan o'tildi!");
      navigate("/");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Ro'yxatdan o'tishda xatolik");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-muted/30">
      <form onSubmit={submit} className="w-full max-w-md bg-background border p-8 rounded-sm space-y-5" data-testid="register-form">
        <div>
          <h2 className="font-heading text-2xl font-semibold tracking-tight">Ro'yxatdan o'tish</h2>
          <p className="text-sm text-muted-foreground mt-1">AI Buxgalter platformasiga xush kelibsiz</p>
        </div>
        <div className="space-y-3">
          <div>
            <Label htmlFor="full">Ism va familiya</Label>
            <Input id="full" required data-testid="reg-fullname"
              value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
          </div>
          <div>
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" required data-testid="reg-email"
              value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </div>
          <div>
            <Label htmlFor="phone">Telefon (ixtiyoriy)</Label>
            <Input id="phone" data-testid="reg-phone" placeholder="+998..."
              value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </div>
          <div>
            <Label htmlFor="password">Parol (kamida 8 belgi)</Label>
            <Input id="password" type="password" required data-testid="reg-password"
              value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </div>
        </div>
        <Button type="submit" disabled={loading} data-testid="register-submit-btn"
          className="w-full bg-emerald-600 hover:bg-emerald-700 rounded-sm">
          {loading ? "Yaratilmoqda..." : "Ro'yxatdan o'tish"}
        </Button>
        <div className="text-sm text-center text-muted-foreground">
          Hisobingiz bormi?{" "}
          <Link to="/login" className="text-emerald-700 hover:underline" data-testid="goto-login-link">
            Kirish
          </Link>
        </div>
      </form>
    </div>
  );
}
