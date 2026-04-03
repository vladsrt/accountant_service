"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  LayoutDashboard,
  FileText,
  CreditCard,
  Settings,
  Cloud,
  MoreHorizontal,
  Eye,
  Pencil,
  Trash2,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Building2,
  Loader2,
} from "lucide-react"
import { apiGet, apiPost } from "@/lib/api"
import { useAuth } from "@/hooks/useAuth"

// Mock data for invoices (will be replaced with real API later)
const mockInvoices = [
  {
    id: "1",
    date: "2024-01-15",
    number: "FV/2024/01/001",
    contractorNip: "5261234567",
    amount: 12500.00,
    status: "classified",
    taxRate: "12%",
  },
  {
    id: "2",
    date: "2024-01-14",
    number: "FV/2024/01/002",
    contractorNip: "7891234560",
    amount: 8750.50,
    status: "review",
    taxRate: null,
  },
  {
    id: "3",
    date: "2024-01-13",
    number: "FV/2024/01/003",
    contractorNip: "1234567890",
    amount: 3200.00,
    status: "processing",
    taxRate: null,
  },
  {
    id: "4",
    date: "2024-01-12",
    number: "FV/2024/01/004",
    contractorNip: "9876543210",
    amount: 15800.00,
    status: "classified",
    taxRate: "8.5%",
  },
  {
    id: "5",
    date: "2024-01-11",
    number: "FV/2024/01/005",
    contractorNip: "5556667778",
    amount: 4500.00,
    status: "classified",
    taxRate: "15%",
  },
  {
    id: "6",
    date: "2024-01-10",
    number: "FV/2024/01/006",
    contractorNip: "1112223334",
    amount: 22000.00,
    status: "review",
    taxRate: null,
  },
]

const navItems = [
  { href: "/dashboard", label: "Panel główny", icon: LayoutDashboard, active: true },
  { href: "/dashboard/invoices", label: "Faktury", icon: FileText, active: false },
  { href: "/dashboard/statements", label: "Wyciągi", icon: CreditCard, active: false },
  { href: "/dashboard/settings", label: "Ustawienia", icon: Settings, active: false },
]

function StatusBadge({ status, taxRate }: { status: string; taxRate: string | null }) {
  if (status === "classified" && taxRate) {
    return (
      <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 border-0 font-medium">
        Ryczałt {taxRate}
      </Badge>
    )
  }
  if (status === "review") {
    return (
      <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-100 border-0 font-medium">
        Wymaga weryfikacji
      </Badge>
    )
  }
  return (
    <Badge className="bg-slate-100 text-slate-600 hover:bg-slate-100 border-0 font-medium">
      Przetwarzanie...
    </Badge>
  )
}

export default function DashboardPage() {
  const router = useRouter()
  const { logout, isAuthenticated } = useAuth()
  const [isSyncing, setIsSyncing] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [companyLoaded, setCompanyLoaded] = useState(false)

  // Check auth + company on mount
  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth")
      return
    }

    apiGet("/api/v1/company/me")
      .then(() => setCompanyLoaded(true))
      .catch((err: Error) => {
        if (err.message.includes("404") || err.message.includes("not found") || err.message.includes("Company not found")) {
          router.push("/onboarding")
        }
      })
  }, [isAuthenticated, router])

  const handleSync = async () => {
    setIsSyncing(true)
    try {
      await apiPost("/api/v1/ksef/sync")
      toast.success("Synchronizacja uruchomiona w tle")
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Błąd synchronizacji"
      toast.error(msg)
    } finally {
      setIsSyncing(false)
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("pl-PL", {
      style: "currency",
      currency: "PLN",
    }).format(amount)
  }

  const formatNip = (nip: string) => {
    return nip.replace(/(\d{3})(\d{3})(\d{2})(\d{2})/, "$1-$2-$3-$4")
  }

  if (!companyLoaded) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    )
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarCollapsed ? "w-20" : "w-64"
        } bg-slate-900 text-white flex flex-col transition-all duration-300 ease-in-out`}
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800">
          {!sidebarCollapsed && (
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center">
                <Building2 className="w-5 h-5 text-white" />
              </div>
              <span className="font-semibold text-lg">KseFAuto</span>
            </div>
          )}
          {sidebarCollapsed && (
            <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center mx-auto">
              <Building2 className="w-5 h-5 text-white" />
            </div>
          )}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-1.5 rounded-md hover:bg-slate-800 transition-colors"
          >
            {sidebarCollapsed ? (
              <ChevronRight className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronLeft className="w-4 h-4 text-slate-400" />
            )}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-6 px-3">
          <ul className="space-y-1">
            {navItems.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                    item.active
                      ? "bg-indigo-600 text-white"
                      : "text-slate-400 hover:text-white hover:bg-slate-800"
                  }`}
                >
                  <item.icon className="w-5 h-5 flex-shrink-0" />
                  {!sidebarCollapsed && <span className="font-medium">{item.label}</span>}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        {/* User / Logout */}
        <div className="p-3 border-t border-slate-800">
          <button
            onClick={logout}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg w-full text-slate-400 hover:text-white hover:bg-slate-800 transition-colors ${
              sidebarCollapsed ? "justify-center" : ""
            }`}
          >
            <LogOut className="w-5 h-5 flex-shrink-0" />
            {!sidebarCollapsed && <span className="font-medium">Wyloguj się</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Panel główny</h1>
            <p className="text-sm text-slate-500">Zarządzaj swoimi fakturami</p>
          </div>
          <Button
            onClick={handleSync}
            disabled={isSyncing}
            className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2"
          >
            <Cloud className={`w-4 h-4 ${isSyncing ? "animate-pulse" : ""}`} />
            {isSyncing ? "Synchronizowanie..." : "Pobierz z KSeF"}
          </Button>
        </header>

        {/* Content */}
        <main className="flex-1 p-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
              <p className="text-sm text-slate-500 mb-1">Wszystkie faktury</p>
              <p className="text-2xl font-bold text-slate-900">{mockInvoices.length}</p>
            </div>
            <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
              <p className="text-sm text-slate-500 mb-1">Do weryfikacji</p>
              <p className="text-2xl font-bold text-amber-600">
                {mockInvoices.filter((i) => i.status === "review").length}
              </p>
            </div>
            <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
              <p className="text-sm text-slate-500 mb-1">Suma netto</p>
              <p className="text-2xl font-bold text-slate-900">
                {formatCurrency(mockInvoices.reduce((sum, i) => sum + i.amount, 0))}
              </p>
            </div>
          </div>

          {/* Invoices Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200">
              <h2 className="text-lg font-semibold text-slate-900">Ostatnie Faktury</h2>
            </div>
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50 hover:bg-slate-50">
                  <TableHead className="font-semibold text-slate-700">Data</TableHead>
                  <TableHead className="font-semibold text-slate-700">Numer Faktury</TableHead>
                  <TableHead className="font-semibold text-slate-700">NIP Kontrahenta</TableHead>
                  <TableHead className="font-semibold text-slate-700 text-right">Kwota (PLN)</TableHead>
                  <TableHead className="font-semibold text-slate-700">Status AI</TableHead>
                  <TableHead className="font-semibold text-slate-700 text-right">Akcje</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mockInvoices.map((invoice) => (
                  <TableRow key={invoice.id} className="hover:bg-slate-50">
                    <TableCell className="text-slate-600">{invoice.date}</TableCell>
                    <TableCell className="font-medium text-slate-900">{invoice.number}</TableCell>
                    <TableCell className="text-slate-600 font-mono text-sm">
                      {formatNip(invoice.contractorNip)}
                    </TableCell>
                    <TableCell className="text-right font-medium text-slate-900">
                      {formatCurrency(invoice.amount)}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={invoice.status} taxRate={invoice.taxRate} />
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="w-4 h-4 text-slate-500" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-40">
                          <DropdownMenuItem className="gap-2 cursor-pointer">
                            <Eye className="w-4 h-4" />
                            Podgląd
                          </DropdownMenuItem>
                          <DropdownMenuItem className="gap-2 cursor-pointer">
                            <Pencil className="w-4 h-4" />
                            Edytuj stawkę
                          </DropdownMenuItem>
                          <DropdownMenuItem className="gap-2 cursor-pointer text-red-600 focus:text-red-600">
                            <Trash2 className="w-4 h-4" />
                            Usuń
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </main>
      </div>
    </div>
  )
}
