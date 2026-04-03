"use client"

import { useState, useCallback, useEffect } from "react"
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
  LayoutDashboard,
  FileText,
  CreditCard,
  Settings,
  Upload,
  FileSpreadsheet,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Building2,
  CheckCircle2,
  AlertCircle,
  Clock,
} from "lucide-react"
import { apiGet, apiPostFile } from "@/lib/api"
import { useAuth } from "@/hooks/useAuth"

const navItems = [
  { href: "/dashboard", label: "Panel główny", icon: LayoutDashboard, active: false },
  { href: "/dashboard/invoices", label: "Faktury", icon: FileText, active: false },
  { href: "/dashboard/statements", label: "Wyciągi", icon: CreditCard, active: true },
  { href: "/dashboard/settings", label: "Ustawienia", icon: Settings, active: false },
]

interface UploadResult {
  total_parsed: number
  new_inserted: number
  duplicates_ignored: number
}

function MatchStatusBadge({ status, invoiceNumber }: { status: string; invoiceNumber: string | null }) {
  if (status === "matched" && invoiceNumber) {
    return (
      <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 border-0 font-medium gap-1.5">
        <CheckCircle2 className="w-3.5 h-3.5" />
        Dopasowano: {invoiceNumber}
      </Badge>
    )
  }
  if (status === "unmatched") {
    return (
      <Badge className="bg-red-100 text-red-700 hover:bg-red-100 border-0 font-medium gap-1.5">
        <AlertCircle className="w-3.5 h-3.5" />
        Brak dopasowania
      </Badge>
    )
  }
  return (
    <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-100 border-0 font-medium gap-1.5">
      <Clock className="w-3.5 h-3.5" />
      Przetwarzanie...
    </Badge>
  )
}

export default function StatementsPage() {
  const router = useRouter()
  const { logout, isAuthenticated } = useAuth()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null)
  const [companyId, setCompanyId] = useState<number | null>(null)

  // Load company to get company_id
  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth")
      return
    }

    apiGet<{ id: number }>("/api/v1/company/me")
      .then((data) => setCompanyId(data.id))
      .catch(() => router.push("/onboarding"))
  }, [isAuthenticated, router])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const files = e.dataTransfer.files
    if (files.length > 0 && files[0].name.endsWith(".csv")) {
      handleFileUpload(files[0])
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyId])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFileUpload(files[0])
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyId])

  const handleFileUpload = async (file: File) => {
    if (!companyId) {
      toast.error("Brak profilu firmy. Dokończ onboarding.")
      return
    }

    setUploadedFile(file)
    setIsUploading(true)
    setUploadResult(null)
    try {
      const result = await apiPostFile<UploadResult>("/api/v1/bank/upload", file, {
        company_id: String(companyId),
      })
      setUploadResult(result)
      toast.success(
        `Dodano ${result.new_inserted} nowych transakcji, ${result.duplicates_ignored} duplikatów pominięto`
      )
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Błąd przesyłania pliku"
      toast.error(msg)
      setUploadedFile(null)
    } finally {
      setIsUploading(false)
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("pl-PL", {
      style: "currency",
      currency: "PLN",
    }).format(amount)
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarCollapsed ? "w-20" : "w-64"
        } bg-slate-900 text-white flex flex-col transition-all duration-300 ease-in-out`}
      >
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
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Import Wyciągów Bankowych</h1>
            <p className="text-sm text-slate-500">Prześlij wyciągi CSV i dopasuj transakcje</p>
          </div>
        </header>

        <main className="flex-1 p-6">
          {/* Drag & Drop Zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`relative mb-6 border-2 border-dashed rounded-xl p-12 text-center transition-all duration-200 ${
              isDragging
                ? "border-indigo-500 bg-indigo-50"
                : "border-slate-300 bg-white hover:border-slate-400"
            }`}
          >
            <input
              type="file"
              accept=".csv"
              onChange={handleFileSelect}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />

            <div className="flex flex-col items-center gap-4">
              {isUploading ? (
                <>
                  <div className="w-16 h-16 rounded-full bg-indigo-100 flex items-center justify-center">
                    <div className="w-8 h-8 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                  </div>
                  <div>
                    <p className="text-lg font-medium text-slate-900">Przetwarzanie pliku...</p>
                    <p className="text-sm text-slate-500 mt-1">{uploadedFile?.name}</p>
                  </div>
                </>
              ) : uploadResult && uploadedFile ? (
                <>
                  <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center">
                    <CheckCircle2 className="w-8 h-8 text-emerald-600" />
                  </div>
                  <div>
                    <p className="text-lg font-medium text-slate-900">Plik przesłany pomyślnie</p>
                    <p className="text-sm text-slate-500 mt-1">{uploadedFile.name}</p>
                    <p className="text-sm text-emerald-600 mt-2 font-medium">
                      Przetworzone: {uploadResult.total_parsed} | Nowe: {uploadResult.new_inserted} | Duplikaty: {uploadResult.duplicates_ignored}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setUploadedFile(null)
                      setUploadResult(null)
                    }}
                    className="mt-2"
                  >
                    Prześlij inny plik
                  </Button>
                </>
              ) : (
                <>
                  <div className={`w-16 h-16 rounded-full flex items-center justify-center transition-colors ${
                    isDragging ? "bg-indigo-200" : "bg-slate-100"
                  }`}>
                    {isDragging ? (
                      <Upload className="w-8 h-8 text-indigo-600" />
                    ) : (
                      <FileSpreadsheet className="w-8 h-8 text-slate-400" />
                    )}
                  </div>
                  <div>
                    <p className="text-lg font-medium text-slate-900">
                      {isDragging ? "Upuść plik tutaj" : "Upuść plik CSV z banku"}
                    </p>
                    <p className="text-sm text-slate-500 mt-1">
                      mBank, PKO BP, ING, Santander, itp. lub{" "}
                      <span className="text-indigo-600 font-medium">kliknij, aby wybrać</span>
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
