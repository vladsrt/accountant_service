"use client"

import { useState } from "react"

interface FAQItem {
  question: string
  answer: string
}

const faqData: FAQItem[] = [
  {
    question: "Czy muszę mieć konto w KSeF żeby korzystać z platformy?",
    answer:
      "Tak, do pełnej funkcjonalności potrzebujesz autoryzacji w Krajowym Systemie e-Faktur. Nasz system przeprowadzi Cię przez proces autoryzacji krok po kroku. Możesz też zacząć od samego importu wyciągów bankowych bez KSeF.",
  },
  {
    question: "Jakie banki są obsługiwane przy imporcie wyciągów?",
    answer:
      "Obsługujemy eksporty CSV ze wszystkich głównych polskich banków: mBank, PKO BP, Pekao, ING, Santander, BNP Paribas, Millennium i wielu innych. System automatycznie rozpoznaje format pliku.",
  },
  {
    question: "Jak działa klasyfikacja AI stawek ryczałtu?",
    answer:
      "Nasz model AI analizuje opis transakcji, dane kontrahenta oraz historię Twoich rozliczeń. Jeśli system ma pewność, automatycznie przypisuje odpowiednią stawkę (np. 12%, 8.5%, 5.5%). Gdy nie jest pewien, oznacza transakcję do ręcznej weryfikacji - to podejście Human-in-the-Loop.",
  },
  {
    question: "Czy mogę anulować subskrypcję w dowolnym momencie?",
    answer:
      "Tak, możesz anulować subskrypcję w każdej chwili bez żadnych opłat. Po anulowaniu zachowujesz dostęp do końca opłaconego okresu, a Twoje dane pozostają dostępne jeszcze przez 30 dni.",
  },
  {
    question: "Czy platforma jest zgodna z RODO?",
    answer:
      "Tak, w pełni przestrzegamy przepisów RODO. Twoje dane są przechowywane na serwerach w UE, są szyfrowane i nigdy nie są udostępniane podmiotom trzecim bez Twojej zgody.",
  },
  {
    question: "Czy mogę wyeksportować dane do mojego biura rachunkowego?",
    answer:
      "Tak, w planie Pro możesz wygenerować eksport w formatach akceptowanych przez popularne programy księgowe (XML, CSV, PDF). Możesz też nadać swojemu księgowemu dostęp tylko do odczytu.",
  },
]

function ChevronDownIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export default function FAQSection() {
  const [openItems, setOpenItems] = useState<number[]>([0])

  const toggleItem = (index: number) => {
    setOpenItems((prev) => (prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index]))
  }

  return (
    <section className="py-20 md:py-28 bg-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex flex-col lg:flex-row gap-16">
          {/* Left Column - Header */}
          <div className="lg:w-1/3">
            <div className="inline-flex items-center gap-2.5 px-4 py-2 bg-white border border-slate-200/60 text-slate-700 text-xs font-semibold rounded-full mb-6 shadow-lg shadow-slate-200/30">
              <svg className="w-4 h-4 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              FAQ
            </div>
            <h2 className="text-4xl md:text-5xl font-extrabold text-slate-900 mb-5 tracking-tighter">
              Często zadawane pytania
            </h2>
            <p className="text-slate-500 text-base leading-relaxed font-medium">
              Wszystko co musisz wiedzieć o naszej platformie do automatyzacji księgowości.
            </p>
            <div className="mt-8">
              <p className="text-slate-400 text-sm mb-3 font-medium">Nie znalazłeś odpowiedzi?</p>
              <button className="text-indigo-600 font-semibold text-sm 
                hover:text-indigo-700 hover:translate-x-1 
                transition-all duration-300 inline-flex items-center gap-1">
                Skontaktuj się z nami 
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>

          {/* Right Column - FAQ Items */}
          <div className="lg:w-2/3">
            <div className="space-y-4">
              {faqData.map((item, index) => {
                const isOpen = openItems.includes(index)

                return (
                  <div 
                    key={index} 
                    className={`bg-white rounded-2xl border overflow-hidden 
                      transition-all duration-500 ease-out
                      ${isOpen 
                        ? "border-indigo-200 shadow-xl shadow-indigo-100/50" 
                        : "border-slate-200/60 hover:border-slate-300 hover:shadow-lg hover:shadow-slate-200/50"
                      }`}
                  >
                    <button
                      onClick={() => toggleItem(index)}
                      className="w-full px-6 py-5 flex justify-between items-center gap-4 text-left 
                        hover:bg-slate-50/50 transition-all duration-300"
                      aria-expanded={isOpen}
                    >
                      <span className="text-slate-900 font-semibold text-base">
                        {item.question}
                      </span>
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 
                        transition-all duration-500
                        ${isOpen 
                          ? "bg-indigo-100 text-indigo-600 rotate-180" 
                          : "bg-slate-100 text-slate-500"
                        }`}>
                        <ChevronDownIcon className="w-5 h-5" />
                      </div>
                    </button>

                    <div
                      className={`overflow-hidden transition-all duration-500 ease-in-out ${
                        isOpen ? "max-h-96 opacity-100" : "max-h-0 opacity-0"
                      }`}
                    >
                      <p className="px-6 pb-5 text-slate-500 text-sm leading-relaxed font-medium">
                        {item.answer}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
