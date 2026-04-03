export default function FooterSection() {
  return (
    <footer className="bg-slate-900 text-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 md:py-20">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-10 mb-16">
          {/* Brand Section */}
          <div className="col-span-2 md:col-span-1">
            <div className="text-2xl font-extrabold mb-5 tracking-tight">
              Księgowość<span className="text-indigo-400">.ai</span>
            </div>
            <p className="text-slate-400 text-sm mb-8 max-w-xs leading-relaxed font-medium">
              Automatyzacja księgowości dla polskich JDG. Inteligentnie, bezpiecznie, bez stresu.
            </p>
            {/* Social Media Icons */}
            <div className="flex gap-3">
              <a href="#" className="w-10 h-10 bg-slate-800 rounded-full flex items-center justify-center 
                hover:bg-indigo-600 hover:scale-110 transition-all duration-300">
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </a>
              <a href="#" className="w-10 h-10 bg-slate-800 rounded-full flex items-center justify-center 
                hover:bg-indigo-600 hover:scale-110 transition-all duration-300">
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M20.5 2h-17A1.5 1.5 0 002 3.5v17A1.5 1.5 0 003.5 22h17a1.5 1.5 0 001.5-1.5v-17A1.5 1.5 0 0020.5 2zM8 19H5v-9h3zM6.5 8.25A1.75 1.75 0 118.3 6.5a1.78 1.78 0 01-1.8 1.75zM19 19h-3v-4.74c0-1.42-.6-1.93-1.38-1.93A1.74 1.74 0 0013 14.19a.66.66 0 000 .14V19h-3v-9h2.9v1.3a3.11 3.11 0 012.7-1.4c1.55 0 3.36.86 3.36 3.66z" />
                </svg>
              </a>
            </div>
          </div>

          {/* Produkt Column */}
          <div>
            <h4 className="text-slate-500 text-xs font-bold uppercase tracking-widest mb-5">Produkt</h4>
            <ul className="space-y-4">
              <li><a href="#" className="text-slate-300 text-sm font-medium hover:text-white hover:translate-x-1 transition-all duration-300 inline-block">Funkcje</a></li>
              <li><a href="#" className="text-slate-300 text-sm font-medium hover:text-white hover:translate-x-1 transition-all duration-300 inline-block">Cennik</a></li>
              <li><a href="#" className="text-slate-300 text-sm font-medium hover:text-white hover:translate-x-1 transition-all duration-300 inline-block">Integracje</a></li>
              <li><a href="#" className="text-slate-300 text-sm font-medium hover:text-white hover:translate-x-1 transition-all duration-300 inline-block">API</a></li>
            </ul>
          </div>

          {/* Firma Column */}
          <div>
            <h4 className="text-slate-500 text-xs font-bold uppercase tracking-widest mb-5">Firma</h4>
            <ul className="space-y-4">
              <li><a href="#" className="text-slate-300 text-sm font-medium hover:text-white hover:translate-x-1 transition-all duration-300 inline-block">O nas</a></li>
              <li><a href="#" className="text-slate-300 text-sm font-medium hover:text-white hover:translate-x-1 transition-all duration-300 inline-block">Kariera</a></li>
              <li><a href="#" className="text-slate-300 text-sm font-medium hover:text-white hover:translate-x-1 transition-all duration-300 inline-block">Blog</a></li>
              <li><a href="#" className="text-slate-300 text-sm font-medium hover:text-white hover:translate-x-1 transition-all duration-300 inline-block">Kontakt</a></li>
            </ul>
          </div>

          {/* Wsparcie Column */}
          <div>
            <h4 className="text-slate-500 text-xs font-bold uppercase tracking-widest mb-5">Wsparcie</h4>
            <ul className="space-y-4">
              <li><a href="#" className="text-slate-300 text-sm font-medium hover:text-white hover:translate-x-1 transition-all duration-300 inline-block">Dokumentacja</a></li>
              <li><a href="#" className="text-slate-300 text-sm font-medium hover:text-white hover:translate-x-1 transition-all duration-300 inline-block">Centrum pomocy</a></li>
              <li><a href="#" className="text-slate-300 text-sm font-medium hover:text-white hover:translate-x-1 transition-all duration-300 inline-block">Status systemu</a></li>
              <li><a href="#" className="text-slate-300 text-sm font-medium hover:text-white hover:translate-x-1 transition-all duration-300 inline-block">Bezpieczeństwo</a></li>
            </ul>
          </div>
        </div>

        {/* Bottom Section */}
        <div className="pt-8 border-t border-slate-800 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-slate-500 text-sm font-medium">
            © 2026 Księgowość.ai. Wszelkie prawa zastrzeżone.
          </p>
          <div className="flex gap-8">
            <a href="#" className="text-slate-500 text-sm font-medium hover:text-slate-300 transition-all duration-300">Regulamin</a>
            <a href="#" className="text-slate-500 text-sm font-medium hover:text-slate-300 transition-all duration-300">Polityka prywatności</a>
            <a href="#" className="text-slate-500 text-sm font-medium hover:text-slate-300 transition-all duration-300">RODO</a>
          </div>
        </div>
      </div>
    </footer>
  )
}
