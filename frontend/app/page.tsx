"use client"

import type React from "react"
import { useState } from "react"
import FAQSection from "../components/faq-section"
import PricingSection from "../components/pricing-section"
import FooterSection from "../components/footer-section"

// Language Switcher Component
function LanguageSwitcher() {
  const [lang, setLang] = useState<"PL" | "EN">("PL")
  
  return (
    <div className="flex items-center gap-1 px-1.5 py-1 bg-white/60 backdrop-blur-sm rounded-full text-xs font-medium border border-slate-200/50">
      <button
        onClick={() => setLang("PL")}
        className={`px-2.5 py-1 rounded-full transition-all duration-300 ${
          lang === "PL" 
            ? "bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-md" 
            : "text-slate-600 hover:text-slate-900"
        }`}
      >
        PL
      </button>
      <button
        onClick={() => setLang("EN")}
        className={`px-2.5 py-1 rounded-full transition-all duration-300 ${
          lang === "EN" 
            ? "bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-md" 
            : "text-slate-600 hover:text-slate-900"
        }`}
      >
        EN
      </button>
    </div>
  )
}

// Reusable Badge Component
function Badge({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="px-4 py-2 bg-white/80 backdrop-blur-sm shadow-lg shadow-slate-200/50 overflow-hidden rounded-full flex items-center gap-2.5 border border-slate-200/50">
      <div className="w-4 h-4 flex items-center justify-center text-indigo-600">{icon}</div>
      <span className="text-slate-700 text-xs font-semibold tracking-wide">{text}</span>
    </div>
  )
}

// Feature Card Component for Bento Grid
function FeatureCard({
  icon,
  title,
  description,
  size = "normal",
}: {
  icon: React.ReactNode
  title: string
  description: string
  size?: "normal" | "large"
}) {
  return (
    <div className={`group relative p-8 bg-white rounded-3xl border border-slate-200/60 
      hover:border-indigo-200 transition-all duration-500 ease-out
      hover:shadow-2xl hover:shadow-indigo-100/50 hover:-translate-y-1
      ${size === "large" ? "md:col-span-2 md:row-span-1" : ""}`}
    >
      {/* Subtle gradient overlay on hover */}
      <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-indigo-50/0 via-transparent to-violet-50/0 
        group-hover:from-indigo-50/50 group-hover:to-violet-50/30 transition-all duration-500 pointer-events-none" />
      
      <div className="relative z-10">
        <div className="w-14 h-14 mb-6 bg-gradient-to-br from-indigo-100 to-violet-100 rounded-2xl 
          flex items-center justify-center text-indigo-600 
          group-hover:scale-110 group-hover:shadow-lg group-hover:shadow-indigo-200/50 
          transition-all duration-500">
          {icon}
        </div>
        <h3 className="text-slate-900 text-lg font-bold mb-3 tracking-tight">{title}</h3>
        <p className="text-slate-600 text-sm leading-relaxed">{description}</p>
      </div>
    </div>
  )
}

// Stats Card Component
function StatCard({ value, label }: { value: string; label: string }) {
  return (
    <div className="flex flex-col items-center p-8 group">
      <div className="text-4xl md:text-5xl font-extrabold bg-gradient-to-r from-indigo-600 to-violet-600 
        bg-clip-text text-transparent mb-2 tracking-tight
        group-hover:scale-105 transition-transform duration-300">{value}</div>
      <div className="text-slate-500 text-sm text-center font-medium">{label}</div>
    </div>
  )
}

// Step Card Component
function StepCard({ number, title, description }: { number: number; title: string; description: string }) {
  return (
    <div className="group text-center p-6 rounded-3xl bg-white border border-slate-200/60 
      hover:border-indigo-200 hover:shadow-xl hover:shadow-indigo-100/30 
      transition-all duration-500 hover:-translate-y-1">
      <div className="w-16 h-16 mx-auto mb-5 bg-gradient-to-br from-indigo-600 to-violet-600 
        text-white rounded-2xl flex items-center justify-center text-2xl font-bold
        group-hover:scale-110 group-hover:shadow-lg group-hover:shadow-indigo-300/50 
        transition-all duration-500">{number}</div>
      <h3 className="text-lg font-bold text-slate-900 mb-2 tracking-tight">{title}</h3>
      <p className="text-slate-500 text-sm leading-relaxed">{description}</p>
    </div>
  )
}

export default function LandingPage() {
  return (
    <div className="w-full min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-50">
      {/* Floating Navigation with Glassmorphism */}
      <header className="fixed top-0 left-0 right-0 z-50 px-4 pt-4">
        <div className="max-w-6xl mx-auto">
          <nav className="flex items-center justify-between h-16 px-6 
            bg-white/70 backdrop-blur-xl border border-slate-100 
            rounded-full shadow-lg shadow-slate-200/30">
            <div className="flex items-center gap-10">
              <div className="text-slate-900 font-extrabold text-xl tracking-tight">
                Księgowość<span className="text-indigo-600">.ai</span>
              </div>
              <div className="hidden md:flex items-center gap-8">
                <button className="text-slate-600 hover:text-slate-900 text-sm font-medium transition-all duration-300 hover:scale-105">
                  Funkcje
                </button>
                <button className="text-slate-600 hover:text-slate-900 text-sm font-medium transition-all duration-300 hover:scale-105">
                  Cennik
                </button>
                <button className="text-slate-600 hover:text-slate-900 text-sm font-medium transition-all duration-300 hover:scale-105">
                  Dokumentacja
                </button>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <LanguageSwitcher />
              <button className="hidden sm:block px-5 py-2.5 text-slate-700 text-sm font-semibold 
                hover:text-slate-900 transition-all duration-300">
                Zaloguj się
              </button>
              <button className="px-6 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 
                text-white text-sm font-semibold rounded-full 
                hover:scale-105 hover:shadow-xl hover:shadow-indigo-300/50 
                transition-all duration-300 ease-out">
                Zacznij za darmo
              </button>
            </div>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-32 pb-20 md:pt-40 md:pb-28">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="max-w-4xl mx-auto text-center">
            <div className="inline-flex items-center gap-2.5 px-5 py-2.5 
              bg-gradient-to-r from-indigo-50 to-violet-50 
              text-indigo-700 text-sm font-semibold rounded-full mb-8
              border border-indigo-100/50">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Dla polskich JDG na ryczałcie
            </div>
            <h1 className="text-5xl md:text-6xl lg:text-7xl font-extrabold text-slate-900 leading-[1.1] mb-8 tracking-tighter">
              Twoja księgowość
              <br />
              <span className="bg-gradient-to-r from-indigo-600 via-violet-600 to-purple-600 bg-clip-text text-transparent">
                na autopilocie
              </span>
            </h1>
            <p className="text-lg md:text-xl text-slate-600 leading-relaxed mb-10 max-w-2xl mx-auto font-medium">
              Bezproblemowa integracja z KSeF 2.0, inteligentne parsowanie wyciągów bankowych 
              i klasyfikacja stawek ryczałtu przez AI.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <button className="w-full sm:w-auto px-10 py-4 
                bg-gradient-to-r from-indigo-600 to-violet-600 
                text-white text-base font-bold rounded-full 
                hover:scale-105 hover:shadow-2xl hover:shadow-indigo-400/40 
                transition-all duration-300 ease-out
                shadow-xl shadow-indigo-300/40">
                Zacznij za darmo
              </button>
              <button className="w-full sm:w-auto px-10 py-4 
                bg-white text-slate-700 text-base font-semibold rounded-full 
                border border-slate-200 
                hover:border-slate-300 hover:bg-slate-50 hover:scale-105 hover:shadow-lg
                transition-all duration-300 ease-out">
                Zobacz demo
              </button>
            </div>
          </div>

          {/* Dashboard Preview */}
          <div className="mt-20 md:mt-24 relative">
            <div className="absolute inset-0 bg-gradient-to-t from-white via-transparent to-transparent z-10 pointer-events-none" />
            <div className="bg-white rounded-[2rem] shadow-2xl shadow-slate-300/40 border border-slate-200/60 overflow-hidden">
              <div className="bg-gradient-to-r from-slate-100 to-slate-50 px-6 py-4 border-b border-slate-200/60 flex items-center gap-3">
                <div className="flex gap-2">
                  <div className="w-3.5 h-3.5 rounded-full bg-red-400 hover:bg-red-500 transition-colors cursor-pointer" />
                  <div className="w-3.5 h-3.5 rounded-full bg-yellow-400 hover:bg-yellow-500 transition-colors cursor-pointer" />
                  <div className="w-3.5 h-3.5 rounded-full bg-green-400 hover:bg-green-500 transition-colors cursor-pointer" />
                </div>
                <div className="ml-4 flex-1 bg-slate-200/70 rounded-full h-7 max-w-md" />
              </div>
              <div className="aspect-[16/9] md:aspect-[16/8] bg-gradient-to-br from-indigo-50/50 via-white to-violet-50/50 flex items-center justify-center">
                <div className="text-center p-8">
                  <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-indigo-100 to-violet-100 rounded-3xl 
                    flex items-center justify-center shadow-lg shadow-indigo-200/50">
                    <svg className="w-10 h-10 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                  <p className="text-slate-500 text-sm font-medium">Panel główny z podglądem faktur i rozliczeń</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section - Bento Grid */}
      <section className="py-20 md:py-28">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-16">
            <Badge
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              }
              text="FUNKCJE"
            />
            <h2 className="text-4xl md:text-5xl font-extrabold text-slate-900 mt-6 mb-5 tracking-tighter">
              Wszystko czego potrzebujesz
            </h2>
            <p className="text-slate-500 text-lg max-w-2xl mx-auto font-medium">
              Kompleksowe narzędzie do zarządzania księgowością Twojej jednoosobowej działalności gospodarczej.
            </p>
          </div>

          {/* Bento Grid Layout */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <FeatureCard
              icon={
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              }
              title="KSeF 2.0 Ready"
              description="Bezpośrednie połączenie z Ministerstwem Finansów. Automatyczne pobieranie faktur sprzedażowych i kosztowych w czasie rzeczywistym."
            />
            <FeatureCard
              icon={
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
              }
              title="Inteligentne Wyciągi"
              description="Wgraj plik CSV z dowolnego polskiego banku. System sam dopasuje transakcje do faktur z KSeF."
            />
            <FeatureCard
              icon={
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              }
              title="Klasyfikacja AI"
              description="Sztuczna inteligencja sama dobiera stawkę podatku. Jeśli ma wątpliwości – zapyta Cię o szczegóły."
            />
            <FeatureCard
              icon={
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              }
              title="Deklaracje JPK"
              description="Automatyczne generowanie plików JPK_V7 gotowych do wysłania do urzędu skarbowego jednym kliknięciem."
            />
            <FeatureCard
              icon={
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              }
              title="Bezpieczeństwo"
              description="Dane szyfrowane end-to-end, przechowywane na serwerach w UE. Pełna zgodność z RODO."
            />
            <FeatureCard
              icon={
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                </svg>
              }
              title="Eksport danych"
              description="Eksportuj rozliczenia w formatach XML, CSV i PDF. Współdziel dostęp z biurem rachunkowym."
            />
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 md:py-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="bg-white rounded-[2rem] border border-slate-200/60 shadow-xl shadow-slate-200/30 overflow-hidden">
            <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-y md:divide-y-0 divide-slate-100">
              <StatCard value="10,000+" label="Przetworzonych faktur" />
              <StatCard value="99.2%" label="Dokładność AI" />
              <StatCard value="5 min" label="Średni czas rozliczenia" />
              <StatCard value="24/7" label="Automatyczna synchronizacja" />
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 md:py-28">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-16">
            <Badge
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 9l3 3m0 0l-3 3m3-3H8m13 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
              text="JAK TO DZIAŁA"
            />
            <h2 className="text-4xl md:text-5xl font-extrabold text-slate-900 mt-6 mb-5 tracking-tighter">
              Trzy proste kroki
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <StepCard 
              number={1} 
              title="Połącz konta" 
              description="Autoryzuj dostęp do KSeF i wgraj wyciągi bankowe z Twojego banku."
            />
            <StepCard 
              number={2} 
              title="AI analizuje" 
              description="Nasz system automatycznie dopasowuje transakcje i klasyfikuje stawki ryczałtu."
            />
            <StepCard 
              number={3} 
              title="Zatwierdź i wyślij" 
              description="Przejrzyj propozycje, zatwierdź i wygeneruj gotową deklarację podatkową."
            />
          </div>
        </div>
      </section>

      {/* Pricing */}
      <PricingSection />

      {/* FAQ */}
      <FAQSection />

      {/* CTA Section */}
      <section className="py-20 md:py-28">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="relative bg-gradient-to-br from-indigo-600 via-violet-600 to-purple-600 rounded-[2.5rem] overflow-hidden p-12 md:p-20">
            {/* Background decorations */}
            <div className="absolute top-0 right-0 w-96 h-96 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
            <div className="absolute bottom-0 left-0 w-96 h-96 bg-white/10 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />
            
            <div className="relative z-10 text-center max-w-2xl mx-auto">
              <h2 className="text-3xl md:text-5xl font-extrabold text-white mb-6 tracking-tight">
                Gotowy na automatyzację księgowości?
              </h2>
              <p className="text-indigo-100 text-lg mb-10 leading-relaxed">
                Dołącz do tysięcy przedsiębiorców, którzy oszczędzają czas i pieniądze dzięki naszemu rozwiązaniu.
              </p>
              <button className="px-10 py-4 bg-white text-indigo-600 text-base font-bold rounded-full 
                hover:scale-105 hover:shadow-2xl hover:shadow-indigo-900/30 
                transition-all duration-300 ease-out">
                Zacznij za darmo
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <FooterSection />
    </div>
  )
}
