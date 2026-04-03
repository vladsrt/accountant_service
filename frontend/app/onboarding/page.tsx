"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Shield, Eye, EyeOff, Building2, Loader2 } from "lucide-react"

export default function OnboardingPage() {
  const [nip, setNip] = useState("")
  const [ksefToken, setKsefToken] = useState("")
  const [showToken, setShowToken] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [nipError, setNipError] = useState("")

  const formatNip = (value: string) => {
    const digits = value.replace(/\D/g, "").slice(0, 10)
    if (digits.length <= 3) return digits
    if (digits.length <= 6) return `${digits.slice(0, 3)}-${digits.slice(3)}`
    if (digits.length <= 8) return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6)}`
    return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6, 8)}-${digits.slice(8)}`
  }

  const handleNipChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatNip(e.target.value)
    setNip(formatted)
    setNipError("")
  }

  const validateNip = (nipValue: string) => {
    const digits = nipValue.replace(/\D/g, "")
    if (digits.length !== 10) {
      return "NIP musi mieć 10 cyfr"
    }
    // Polish NIP checksum validation
    const weights = [6, 5, 7, 2, 3, 4, 5, 6, 7]
    let sum = 0
    for (let i = 0; i < 9; i++) {
      sum += parseInt(digits[i]) * weights[i]
    }
    const checksum = sum % 11
    if (checksum !== parseInt(digits[9])) {
      return "Nieprawidłowy numer NIP"
    }
    return ""
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const nipValidation = validateNip(nip)
    if (nipValidation) {
      setNipError(nipValidation)
      return
    }

    if (!ksefToken.trim()) {
      return
    }

    setIsLoading(true)
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500))
    setIsLoading(false)
    // Redirect to dashboard after successful setup
    window.location.href = "/dashboard"
  }

  const isFormValid = nip.replace(/\D/g, "").length === 10 && ksefToken.trim().length > 0

  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Step indicator */}
        <div className="text-center mb-6">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-indigo-50 text-indigo-700">
            Krok 1 z 1
          </span>
        </div>

        <Card className="border-0 shadow-xl shadow-slate-200/50">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center mb-4">
              <Building2 className="w-6 h-6 text-indigo-600" />
            </div>
            <CardTitle className="text-2xl font-bold text-slate-900">
              Połącz swoją firmę
            </CardTitle>
            <CardDescription className="text-slate-500 mt-2">
              Wprowadź dane, aby zsynchronizować KSeF
            </CardDescription>
          </CardHeader>

          <CardContent className="pt-4">
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* NIP Input */}
              <div className="space-y-2">
                <Label htmlFor="nip" className="text-sm font-medium text-slate-700">
                  NIP
                </Label>
                <Input
                  id="nip"
                  type="text"
                  placeholder="000-000-00-00"
                  value={nip}
                  onChange={handleNipChange}
                  className={`h-12 text-base font-mono tracking-wider ${
                    nipError 
                      ? "border-red-300 focus-visible:ring-red-500" 
                      : "border-slate-200 focus-visible:ring-indigo-500"
                  }`}
                />
                {nipError && (
                  <p className="text-sm text-red-600">{nipError}</p>
                )}
              </div>

              {/* KSeF Token Input */}
              <div className="space-y-2">
                <Label htmlFor="ksef-token" className="text-sm font-medium text-slate-700">
                  Token KSeF
                </Label>
                <div className="relative">
                  <Input
                    id="ksef-token"
                    type={showToken ? "text" : "password"}
                    placeholder="Wklej token autoryzacyjny..."
                    value={ksefToken}
                    onChange={(e) => setKsefToken(e.target.value)}
                    className="h-12 pr-12 text-base font-mono border-slate-200 focus-visible:ring-indigo-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowToken(!showToken)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    {showToken ? (
                      <EyeOff className="w-5 h-5" />
                    ) : (
                      <Eye className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </div>

              {/* Security Alert */}
              <Alert className="bg-indigo-50 border-indigo-100">
                <Shield className="h-4 w-4 text-indigo-600" />
                <AlertDescription className="text-indigo-700 text-sm ml-2">
                  Twój token jest szyfrowany end-to-end (Fernet) i w pełni bezpieczny.
                </AlertDescription>
              </Alert>

              {/* Submit Button */}
              <Button
                type="submit"
                disabled={!isFormValid || isLoading}
                className="w-full h-12 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-base rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    Łączenie...
                  </>
                ) : (
                  "Zapisz i kontynuuj"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Help link */}
        <p className="text-center text-sm text-slate-500 mt-6">
          Potrzebujesz pomocy?{" "}
          <a href="#" className="text-indigo-600 hover:text-indigo-700 font-medium">
            Jak uzyskać token KSeF
          </a>
        </p>
      </div>
    </div>
  )
}
