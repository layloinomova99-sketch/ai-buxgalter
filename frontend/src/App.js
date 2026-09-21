import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { CompanyProvider } from "@/context/CompanyContext";
import { AppShell } from "@/components/app/AppShell";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Dashboard from "@/pages/Dashboard";
import Companies from "@/pages/Companies";
import Receipts from "@/pages/Receipts";
import Products from "@/pages/Products";
import Mappings from "@/pages/Mappings";
import Rules from "@/pages/Rules";
import AIChat from "@/pages/AIChat";
import Audit from "@/pages/Audit";
import CreatorUsers from "@/pages/CreatorUsers";
import Knowledge from "@/pages/Knowledge";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center text-muted-foreground">Yuklanmoqda...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return (
    <CompanyProvider>
      <AppShell>{children}</AppShell>
    </CompanyProvider>
  );
}

function CreatorOnly({ children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "creator") return <Navigate to="/" replace />;
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<Protected><Dashboard /></Protected>} />
      <Route path="/kompaniyalar" element={<Protected><Companies /></Protected>} />
      <Route path="/cheklar" element={<Protected><Receipts /></Protected>} />
      <Route path="/mahsulotlar" element={<Protected><Products /></Protected>} />
      <Route path="/mappinglar" element={<Protected><Mappings /></Protected>} />
      <Route path="/qoidalar" element={<Protected><Rules /></Protected>} />
      <Route path="/ai" element={<Protected><AIChat /></Protected>} />
      <Route path="/audit" element={<Protected><Audit /></Protected>} />
      <Route path="/creator/foydalanuvchilar" element={<Protected><CreatorOnly><CreatorUsers /></CreatorOnly></Protected>} />
      <Route path="/creator/bilim" element={<Protected><CreatorOnly><Knowledge /></CreatorOnly></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
          <Toaster position="top-right" richColors />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
