"use client"

import { useState, useCallback, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import {
  LayoutDashboard,
  FileText,
  CreditCard,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Building2,
  CheckCircle2,
  Loader2,
  AlertTriangle,
  MessageSquareText,
  Bot,
  Send,
} from "lucide-react"
import { apiGet, resolvePendingLine } from "@/lib/api"
import { useAuth } from "@/hooks/useAuth"

const navItems = [
  { href: "/dashboard", label: "Panel główny", icon: LayoutDashboard, active: false },
  { href: "/dashboard/invoices", label: "Faktury", icon: FileText, active: false },
  { href: "/dashboard/statements", label: "Wyciągi", icon: CreditCard, active: false },
  { href: "/dashboard/pending", label: "Do wyjaśnienia", icon: MessageSquareText, active: true },
  { href: "/dashboard/settings", label: "Ustawienia", icon: Settings, active: false },
]

interface PendingLine {
  line_index: number
  p7_text: string
  clarification_question: string | null
  ambiguity_flags: string[] | null
}

interface PendingInvoice {
  invoice_id: number
  invoice_number: string | null
  questions: PendingLine[]
}

// Unique key for per-line loading/answer state
type LineKey = `${number}_${number}`

function makeKey(invoiceId: number, lineIndex: number): LineKey {
  return `${invoiceId}_${lineIndex}`
}

export default function PendingPage() {
  const router = useRouter()
  const { logout, isAuthenticated } = useAuth()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const [invoices, setInvoices] = useState<PendingInvoice[]>([])
  const [isPageLoading, setIsPageLoading] = useState(true)
  const [answers, setAnswers] = useState<Record<LineKey, string>>({})
  const [loadingLines, setLoadingLines] = useState<Record<LineKey, boolean>>({})

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth")
      return
    }

    setIsPageLoading(true)
    apiGet<PendingInvoice[]>("/api/v1/classification/pending")
      .then((data) => setInvoices(data))
      .catch(() => toast.error("Nie udało się załadować danych"))
      .finally(() => setIsPageLoading(false))
  }, [isAuthenticated, router])

  const setAnswer = useCallback((key: LineKey, value: string) => {
    setAnswers((prev) => ({ ...prev, [key]: value }))
  }, [])

  const handleSubmit = useCallback(
    async (invoiceId: number, lineIndex: number) => {
      const key = makeKey(invoiceId, lineIndex)
      const answer = answers[key]?.trim()
      if (!answer) {
        toast.error("Wprowadź odpowiedź przed wysłaniem")
        return
      }

      setLoadingLines((prev) => ({ ...prev, [key]: true }))

      try {
        await resolvePendingLine(invoiceId, lineIndex, answer)
        toast.success("Pozycja klasyfikowana!")

        // Remove the resolved line from local state
        setInvoices((prev) =>
          prev
            .map((inv) => {
              if (inv.invoice_id !== invoiceId) return inv
              return {
                ...inv,
                questions: inv.questions.filter((q) => q.line_index !== lineIndex),
              }
            })
            .filter((inv) => inv.questions.length > 0)
        )

        // Clean up answer state
        setAnswers((prev) => {
          const next = { ...prev }
          delete next[key]
          return next
        })
      } catch {
        toast.error("Błąd przy zapisie klasyfikacji")
      } finally {
        setLoadingLines((prev) => ({ ...prev, [key]: false }))
      }
    },
    [answers]
  )

  // Count total pending lines
  const totalPending = invoices.reduce((sum, inv) => sum + inv.questions.length, 0)

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Sidebar */}
      <aside
        className={`${sidebarCollapsed ? "w-20" : "w-64"
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
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${item.active
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
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg w-full text-slate-400 hover:text-white hover:bg-slate-800 transition-colors ${sidebarCollapsed ? "justify-center" : ""
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
            <h1 className="text-xl font-semibold text-slate-900">Pozycje do wyjaśnienia</h1>
            <p className="text-sm text-slate-500">
              Mamy pytania do {totalPending} pozycji — odpowiedz, aby zakończyć klasyfikację
            </p>
          </div>
          {totalPending > 0 && (
            <Badge className="bg-amber-100 text-amber-700 border-0 text-sm px-3 py-1">
              <AlertTriangle className="w-4 h-4 mr-1.5" />
              {totalPending} oczekuje
            </Badge>
          )}
        </header>

        <main className="flex-1 p-6 overflow-y-auto">
          {/* Loading state */}
          {isPageLoading && (
            <div className="flex flex-col items-center justify-center py-24">
              <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
              <p className="mt-4 text-slate-500 font-medium">Ładowanie danych...</p>
            </div>
          )}

          {/* Empty state */}
          {!isPageLoading && invoices.length === 0 && (
            <div className="flex flex-col items-center justify-center py-24">
              <div className="w-20 h-20 rounded-full bg-emerald-100 flex items-center justify-center mb-6">
                <CheckCircle2 className="w-10 h-10 text-emerald-600" />
              </div>
              <h2 className="text-2xl font-semibold text-slate-900 mb-2">Wszystko jasne!</h2>
              <p className="text-slate-500 text-lg">Nie ma pytań do pozycji — klasyfikacja zakończona 🎉</p>
            </div>
          )}

          {/* Pending cards */}
          {!isPageLoading && invoices.length > 0 && (
            <div className="space-y-6 max-w-3xl mx-auto">
              {invoices.map((inv) =>
                inv.questions.map((line) => {
                  const key = makeKey(inv.invoice_id, line.line_index)
                  const isSubmitting = loadingLines[key] || false
                  const answer = answers[key] || ""

                  return (
                    <Card key={key} className="border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-base font-semibold text-slate-800">
                            Faktura: {inv.invoice_number || `#${inv.invoice_id}`}
                          </CardTitle>
                          <Badge className="bg-slate-100 text-slate-600 border-0 text-xs">
                            Linia {line.line_index + 1}
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {/* Original P_7 text */}
                        <div>
                          <p className="text-xs font-medium uppercase tracking-wider text-slate-400 mb-1">
                            Oryginalny tekst z faktury:
                          </p>
                          <p className="text-sm text-slate-700 bg-slate-50 rounded-lg p-3 border border-slate-100">
                            {line.p7_text}
                          </p>
                        </div>

                        {/* AI question */}
                        {line.clarification_question && (
                          <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4">
                            <div className="flex items-start gap-3">
                              <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                                <Bot className="w-4.5 h-4.5 text-indigo-600" />
                              </div>
                              <div>
                                <p className="text-xs font-medium uppercase tracking-wider text-indigo-400 mb-1">
                                  Pytanie
                                </p>
                                <p className="text-sm text-indigo-900 font-medium leading-relaxed">
                                  {line.clarification_question}
                                </p>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Ambiguity flags */}
                        {line.ambiguity_flags && line.ambiguity_flags.length > 0 && (
                          <div className="flex flex-wrap gap-1.5">
                            {line.ambiguity_flags.map((flag) => (
                              <Badge key={flag} className="bg-amber-50 text-amber-600 border border-amber-200 text-xs">
                                {flag}
                              </Badge>
                            ))}
                          </div>
                        )}

                        {/* Answer textarea + submit */}
                        <div className="space-y-3 pt-2">
                          <Textarea
                            placeholder="Twoja odpowiedź…"
                            value={answer}
                            onChange={(e) => setAnswer(key, e.target.value)}
                            disabled={isSubmitting}
                            className="min-h-[80px] resize-none text-sm"
                          />
                          <Button
                            onClick={() => handleSubmit(inv.invoice_id, line.line_index)}
                            disabled={isSubmitting || !answer.trim()}
                            className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2"
                          >
                            {isSubmitting ? (
                              <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Przetwarzanie...
                              </>
                            ) : (
                              <>
                                <Send className="w-4 h-4" />
                                Wyślij odpowiedź
                              </>
                            )}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )
                })
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
