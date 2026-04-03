"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { toast } from "sonner"
import {
  LayoutDashboard,
  FileText,
  Building2,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Unplug,
  AlertTriangle,
  Trash2,
  Eye,
  EyeOff,
  Shield,
  Loader2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { apiGet, apiDelete } from "@/lib/api"
import { useAuth } from "@/hooks/useAuth"

const navItems = [
  { icon: LayoutDashboard, label: "Panel główny", href: "/dashboard" },
  { icon: FileText, label: "Faktury", href: "/dashboard/invoices" },
  { icon: Building2, label: "Wyciągi", href: "/dashboard/statements" },
  { icon: Settings, label: "Ustawienia", href: "/dashboard/settings", active: true },
]

interface CompanyProfile {
  id: number
  nip: string
  ksef_token: string | null
}

export default function SettingsPage() {
  const router = useRouter()
  const { logout, isAuthenticated } = useAuth()

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [password, setPassword] = useState("")
  const [isDisconnecting, setIsDisconnecting] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [disconnectDialogOpen, setDisconnectDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)

  const [company, setCompany] = useState<CompanyProfile | null>(null)
  const [loadingCompany, setLoadingCompany] = useState(true)

  // Load company on mount
  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth")
      return
    }

    apiGet<CompanyProfile>("/api/v1/company/me")
      .then((data) => setCompany(data))
      .catch(() => setCompany(null))
      .finally(() => setLoadingCompany(false))
  }, [isAuthenticated, router])

  const formatNip = (nip: string) => {
    return nip.replace(/(\d{3})(\d{3})(\d{2})(\d{2})/, "$1-$2-$3-$4")
  }

  const handleDisconnectKsef = async () => {
    setIsDisconnecting(true)
    try {
      await apiDelete("/api/v1/ksef/token")
      toast.success("KSeF odłączony pomyślnie")
      setCompany((prev) => prev ? { ...prev, ksef_token: null } : null)
      setDisconnectDialogOpen(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Błąd odłączania KSeF"
      toast.error(msg)
    } finally {
      setIsDisconnecting(false)
    }
  }

  const handleDeleteAccount = async () => {
    if (password.length < 6) return
    setIsDeleting(true)
    try {
      await apiDelete("/api/v1/users/me", { password })
      toast.success("Konto usunięte pomyślnie")
      logout()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Błąd usuwania konta"
      toast.error(msg)
    } finally {
      setIsDeleting(false)
      setDeleteDialogOpen(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <aside
        className={`bg-slate-900 text-white flex flex-col transition-all duration-300 ${
          sidebarCollapsed ? "w-16" : "w-64"
        }`}
      >
        <div className="p-4 border-b border-slate-700 flex items-center justify-between">
          {!sidebarCollapsed && (
            <span className="text-xl font-bold tracking-tight">Autopilot</span>
          )}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          >
            {sidebarCollapsed ? (
              <ChevronRight className="h-5 w-5" />
            ) : (
              <ChevronLeft className="h-5 w-5" />
            )}
          </button>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                item.active
                  ? "bg-indigo-600 text-white"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              }`}
            >
              <item.icon className="h-5 w-5 flex-shrink-0" />
              {!sidebarCollapsed && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>

        <div className="p-3 border-t border-slate-700">
          <button
            onClick={logout}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition-colors w-full"
          >
            <LogOut className="h-5 w-5 flex-shrink-0" />
            {!sidebarCollapsed && <span>Wyloguj się</span>}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col">
        <header className="bg-white border-b border-slate-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Ustawienia</h1>
              <p className="text-sm text-slate-500 mt-0.5">Zarządzaj integracjami i kontem</p>
            </div>
          </div>
        </header>

        <main className="flex-1 p-6">
          <div className="max-w-2xl mx-auto space-y-6">
            {/* KSeF Integration Card */}
            <Card className="border-slate-200 shadow-sm">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-indigo-100 rounded-lg">
                    <Shield className="h-5 w-5 text-indigo-600" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">Integracja KSeF</CardTitle>
                    <CardDescription>Połączenie z Krajowym Systemem e-Faktur</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {loadingCompany ? (
                  <div className="flex justify-center py-4">
                    <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
                  </div>
                ) : company ? (
                  <>
                    <div className="bg-slate-50 rounded-lg p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-600">NIP firmy</span>
                        <span className="font-mono font-medium text-slate-900">
                          {formatNip(company.nip)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-600">Status KSeF</span>
                        {company.ksef_token ? (
                          <span className="inline-flex items-center gap-1.5 text-sm font-medium text-emerald-700">
                            <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
                            Aktywne
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500">
                            <span className="w-2 h-2 bg-slate-400 rounded-full"></span>
                            Niepołączony
                          </span>
                        )}
                      </div>
                    </div>

                    {company.ksef_token && (
                      <Dialog open={disconnectDialogOpen} onOpenChange={setDisconnectDialogOpen}>
                        <DialogTrigger asChild>
                          <Button
                            variant="outline"
                            className="w-full border-red-300 text-red-600 hover:bg-red-50 hover:text-red-700 hover:border-red-400"
                          >
                            <Unplug className="h-4 w-4 mr-2" />
                            Odłącz KSeF
                          </Button>
                        </DialogTrigger>
                        <DialogContent>
                          <DialogHeader>
                            <DialogTitle>Odłączyć integrację KSeF?</DialogTitle>
                            <DialogDescription>
                              Po odłączeniu nie będziesz mógł automatycznie pobierać faktur.
                              Twoje dane pozostaną w systemie.
                            </DialogDescription>
                          </DialogHeader>
                          <DialogFooter className="gap-2 sm:gap-0">
                            <Button
                              variant="outline"
                              onClick={() => setDisconnectDialogOpen(false)}
                            >
                              Anuluj
                            </Button>
                            <Button
                              variant="destructive"
                              onClick={handleDisconnectKsef}
                              disabled={isDisconnecting}
                            >
                              {isDisconnecting ? (
                                <>
                                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                  Odłączanie...
                                </>
                              ) : (
                                "Odłącz"
                              )}
                            </Button>
                          </DialogFooter>
                        </DialogContent>
                      </Dialog>
                    )}
                  </>
                ) : (
                  <p className="text-sm text-slate-500 py-2">
                    Brak profilu firmy.{" "}
                    <Link href="/onboarding" className="text-indigo-600 hover:underline">
                      Dokończ onboarding →
                    </Link>
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Danger Zone Card */}
            <Card className="border-red-200 shadow-sm">
              <CardHeader className="border-b border-red-100 bg-red-50/50">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-red-100 rounded-lg">
                    <AlertTriangle className="h-5 w-5 text-red-600" />
                  </div>
                  <div>
                    <CardTitle className="text-lg text-red-900">Strefa niebezpieczna</CardTitle>
                    <CardDescription className="text-red-700/70">
                      Nieodwracalne akcje dotyczące Twojego konta
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-6 space-y-4">
                <div>
                  <h3 className="font-semibold text-slate-900 mb-1">Usuń konto (GDPR)</h3>
                  <p className="text-sm text-slate-600 leading-relaxed">
                    Ta akcja trwale usunie wszystkie Twoje dane, faktury i tokeny.
                    Operacja jest nieodwracalna i zgodna z wymogami RODO.
                  </p>
                </div>

                <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                  <DialogTrigger asChild>
                    <Button
                      variant="destructive"
                      className="w-full bg-red-600 hover:bg-red-700"
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Usuń konto bezpowrotnie
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle className="text-red-900">Usunąć konto?</DialogTitle>
                      <DialogDescription className="text-slate-600">
                        Ta akcja jest nieodwracalna. Wszystkie Twoje dane, faktury,
                        wyciągi bankowe i tokeny zostaną trwale usunięte.
                      </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-3 py-2">
                      <Label htmlFor="confirm-password" className="text-sm font-medium">
                        Wprowadź hasło, aby potwierdzić
                      </Label>
                      <div className="relative">
                        <Input
                          id="confirm-password"
                          type={showPassword ? "text" : "password"}
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          placeholder="Twoje hasło"
                          className="pr-10"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        >
                          {showPassword ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </div>

                    <DialogFooter className="gap-2 sm:gap-0">
                      <Button
                        variant="outline"
                        onClick={() => {
                          setDeleteDialogOpen(false)
                          setPassword("")
                        }}
                      >
                        Anuluj
                      </Button>
                      <Button
                        variant="destructive"
                        onClick={handleDeleteAccount}
                        disabled={isDeleting || password.length < 6}
                        className="bg-red-600 hover:bg-red-700"
                      >
                        {isDeleting ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Usuwanie...
                          </>
                        ) : (
                          <>
                            <Trash2 className="h-4 w-4 mr-2" />
                            Usuń bezpowrotnie
                          </>
                        )}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </CardContent>
            </Card>
          </div>
        </main>
      </div>
    </div>
  )
}
