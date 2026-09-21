import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Building2, Receipt, Package, GitCompareArrows, ScrollText,
  Sparkles, ShieldCheck, Users, Settings, LogOut, Sun, Moon, ChevronDown, BookOpen,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useCompany } from "@/context/CompanyContext";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTheme } from "next-themes";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, testid: "nav-dashboard" },
  { to: "/kompaniyalar", label: "Kompaniyalar", icon: Building2, testid: "nav-companies" },
  { to: "/cheklar", label: "Cheklar", icon: Receipt, testid: "nav-receipts" },
  { to: "/mahsulotlar", label: "Mahsulotlar", icon: Package, testid: "nav-products" },
  { to: "/mappinglar", label: "Mappinglar", icon: GitCompareArrows, testid: "nav-mappings" },
  { to: "/qoidalar", label: "Qoidalar", icon: ScrollText, testid: "nav-rules" },
  { to: "/ai", label: "AI Yordamchi", icon: Sparkles, testid: "nav-ai" },
  { to: "/audit", label: "Audit", icon: ShieldCheck, testid: "nav-audit" },
];

const CREATOR_NAV = [
  { to: "/creator/foydalanuvchilar", label: "Foydalanuvchilar", icon: Users, testid: "nav-creator-users" },
  { to: "/creator/bilim", label: "Bilim bazasi", icon: BookOpen, testid: "nav-creator-knowledge" },
];

export function AppShell({ children }) {
  const { user, logout } = useAuth();
  const { companies, active, setActive } = useCompany();
  const navigate = useNavigate();
  const { theme, setTheme } = useTheme();
  const isCreator = user?.role === "creator";

  return (
    <div className="min-h-screen flex bg-background text-foreground">
      <aside className="hidden md:flex w-64 flex-col border-r bg-muted/40" data-testid="app-sidebar">
        <div className="h-16 flex items-center px-5 border-b">
          <div className="font-heading text-lg font-bold tracking-tight">AI BUXGALTER</div>
        </div>
        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-0.5 text-sm">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"}
              data-testid={n.testid}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-sm transition-colors duration-150 ${
                  isActive ? "bg-emerald-600 text-white" : "hover:bg-accent"
                }`}>
              <n.icon className="h-4 w-4" /> {n.label}
            </NavLink>
          ))}
          {isCreator && (
            <>
              <div className="pt-4 pb-1 px-3 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">Creator</div>
              {CREATOR_NAV.map((n) => (
                <NavLink key={n.to} to={n.to} data-testid={n.testid}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-sm transition-colors duration-150 ${
                      isActive ? "bg-emerald-600 text-white" : "hover:bg-accent"
                    }`}>
                  <n.icon className="h-4 w-4" /> {n.label}
                </NavLink>
              ))}
            </>
          )}
        </nav>
        <div className="p-3 border-t text-xs text-muted-foreground">
          v0.1 · {user?.email}
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b bg-background/80 backdrop-blur-md sticky top-0 z-30 flex items-center px-4 md:px-6 gap-4">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" data-testid="company-switcher-dropdown" className="gap-2 rounded-sm">
                <Building2 className="h-4 w-4" />
                {active ? active.name : "Kompaniya tanlanmagan"}
                <ChevronDown className="h-3 w-3 opacity-60" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-72">
              <DropdownMenuLabel>Kompaniyalaringiz ({companies.length}/10)</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {companies.length === 0 && (
                <div className="px-3 py-4 text-sm text-muted-foreground">Hali kompaniya qo'shmagansiz.</div>
              )}
              {companies.map((c) => (
                <DropdownMenuItem key={c.id} onClick={() => setActive(c.id)} data-testid={`company-option-${c.id}`}>
                  <div className="flex flex-col">
                    <span className="font-medium">{c.name}</span>
                    {c.inn && <span className="text-xs text-muted-foreground">INN: {c.inn}</span>}
                  </div>
                </DropdownMenuItem>
              ))}
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate("/kompaniyalar")} data-testid="add-company-nav-btn">
                + Yangi kompaniya qo'shish
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <div className="ml-auto flex items-center gap-2">
            <Badge variant="outline" className="rounded-sm" data-testid="user-role-badge">
              {user?.role === "creator" ? "Creator" : user?.role === "administrator" ? "Administrator" : "Observer"}
            </Badge>
            <Button variant="ghost" size="icon" data-testid="theme-toggle-btn"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
            <Button variant="ghost" size="icon" data-testid="logout-btn"
              onClick={() => { logout(); navigate("/login"); }}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </header>

        <main className="flex-1 min-w-0 overflow-x-hidden">{children}</main>
      </div>
    </div>
  );
}
