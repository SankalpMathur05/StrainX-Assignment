import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { ThemeProvider } from "@/components/layout/ThemeProvider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: "StrainX · Quote Compare",
  description: "Like-for-like supplier quote comparison, risk flags and a recommendation in one minute.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    // next-themes sets the `dark` class on <html> before hydration, hence the warning suppression.
    <html lang="en" suppressHydrationWarning className={`${inter.variable} ${spaceGrotesk.variable}`}>
      <body className="min-h-dvh">
        <ThemeProvider>
          <SiteHeader />
          <main className="mx-auto w-full max-w-7xl px-4 pb-28 pt-6 md:px-8 md:pt-10 print:p-0">
            {children}
          </main>
          <footer className="mx-auto w-full max-w-7xl border-t border-line px-4 py-6 md:px-8 print:py-2">
            <p className="micro">Figures in INR · GST shown separately as potential input tax credit</p>
          </footer>
        </ThemeProvider>
      </body>
    </html>
  );
}
