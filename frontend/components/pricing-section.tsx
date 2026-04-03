"use client"

export default function PricingSection() {
  return (
    <section className="py-20 md:py-28 bg-gradient-to-b from-slate-50 to-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2.5 px-4 py-2 bg-white/80 backdrop-blur-sm border border-slate-200/50 text-slate-700 text-xs font-semibold rounded-full mb-4 shadow-lg shadow-slate-200/30">
            <svg className="w-4 h-4 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            CENNIK
          </div>
          <h2 className="text-4xl md:text-5xl font-extrabold text-slate-900 mb-5 tracking-tighter">
            Prosty i przejrzysty cennik
          </h2>
          <p className="text-slate-500 text-lg max-w-xl mx-auto font-medium">
            Wybierz plan dopasowany do Twoich potrzeb. Zacznij za darmo, ulepsz gdy będziesz gotowy.
          </p>
        </div>

        {/* Pricing Cards - Bento Style */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Free Plan */}
          <div className="group bg-white rounded-[2rem] border border-slate-200/60 p-10 
            shadow-xl shadow-slate-200/30 
            hover:shadow-2xl hover:shadow-slate-300/40 hover:-translate-y-1 
            transition-all duration-500">
            <div className="mb-8">
              <h3 className="text-slate-900 text-2xl font-bold mb-2 tracking-tight">Darmowy</h3>
              <p className="text-slate-500 text-sm font-medium">Idealny na start i testowanie platformy</p>
            </div>

            <div className="mb-8">
              <div className="flex items-baseline gap-1">
                <span className="text-5xl font-extrabold text-slate-900 tracking-tight">0 zł</span>
                <span className="text-slate-400 text-sm font-medium">/ miesiąc</span>
              </div>
            </div>

            <button className="w-full py-4 px-6 bg-slate-100 text-slate-700 font-semibold rounded-full 
              hover:bg-slate-200 hover:scale-[1.02] 
              transition-all duration-300 mb-10">
              Zacznij za darmo
            </button>

            <ul className="space-y-5">
              {[
                "Do 10 faktur miesięcznie",
                "Podstawowa integracja z KSeF",
                "Import wyciągów CSV",
                "Klasyfikacja AI (podstawowa)",
                "Wsparcie email",
              ].map((feature, index) => (
                <li key={index} className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-slate-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <svg className="w-3 h-3 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span className="text-slate-600 text-sm font-medium">{feature}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Pro Plan - Premium with Glowing Border */}
          <div className="group relative">
            {/* Glowing border effect */}
            <div className="absolute -inset-[2px] bg-gradient-to-r from-indigo-500 via-violet-500 to-purple-500 rounded-[2.2rem] 
              opacity-100 blur-sm group-hover:blur-md group-hover:opacity-100 
              transition-all duration-500" />
            
            <div className="relative bg-gradient-to-br from-indigo-600 via-violet-600 to-purple-600 rounded-[2rem] p-10 
              shadow-2xl shadow-indigo-500/30 overflow-hidden">
              {/* Background decoration */}
              <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
              
              {/* Popular badge */}
              <div className="absolute top-6 right-6">
                <span className="px-4 py-1.5 bg-white/20 backdrop-blur-sm text-white text-xs font-bold rounded-full border border-white/20">
                  Najpopularniejszy
                </span>
              </div>

              <div className="relative z-10">
                <div className="mb-8">
                  <h3 className="text-white text-2xl font-bold mb-2 tracking-tight">Pro</h3>
                  <p className="text-indigo-200 text-sm font-medium">Dla aktywnych przedsiębiorców</p>
                </div>

                <div className="mb-8">
                  <div className="flex items-baseline gap-1">
                    <span className="text-5xl font-extrabold text-white tracking-tight">49 zł</span>
                    <span className="text-indigo-200 text-sm font-medium">/ miesiąc</span>
                  </div>
                </div>

                <button className="w-full py-4 px-6 bg-white text-indigo-600 font-bold rounded-full 
                  hover:bg-indigo-50 hover:scale-[1.02] hover:shadow-xl hover:shadow-white/20
                  transition-all duration-300 mb-10">
                  Wybierz Pro
                </button>

                <ul className="space-y-5">
                  {[
                    "Nielimitowane faktury",
                    "Pełna integracja z KSeF 2.0",
                    "Automatyczny import z banków",
                    "Zaawansowana klasyfikacja AI",
                    "Human-in-the-Loop weryfikacja",
                    "Generowanie deklaracji JPK",
                    "Priorytetowe wsparcie",
                    "Eksport do biura rachunkowego",
                  ].map((feature, index) => (
                    <li key={index} className="flex items-start gap-3">
                      <div className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <span className="text-white text-sm font-medium">{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Trust note */}
        <div className="mt-16 text-center">
          <p className="text-slate-400 text-sm font-medium">
            Bezpieczne płatności przez Stripe. Możesz anulować w każdej chwili.
          </p>
        </div>
      </div>
    </section>
  )
}
