import type { Metadata } from "next";
import { JetBrains_Mono, Public_Sans } from "next/font/google";
import "./globals.css";

const publicSans = Public_Sans({
  variable: "--font-public-sans",
  subsets: ["latin"],
});

const jetBrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Brasaland Talent Pipeline",
  description: "Herramienta interna de People & Talent para el seguimiento de candidaturas.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${publicSans.variable} ${jetBrainsMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <div className="app-shell min-h-full flex flex-col">
          <header className="border-b border-amber-200/70 bg-white/90 backdrop-blur">
            <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-3 md:px-10">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-amber-700">Brasaland</p>
                <p className="text-sm font-semibold text-zinc-900">People & Talent Console</p>
              </div>
              <span className="rounded-full border border-amber-300 bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
                Uso interno
              </span>
            </div>
          </header>

          {children}
        </div>
      </body>
    </html>
  );
}
