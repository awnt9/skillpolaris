import type { Metadata } from "next";
import Navbar from "@/components/Navbar";
import Sparkles from "@/components/Sparkles";
import "./globals.css";
import { Geist } from "next/font/google";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

export const metadata: Metadata = {
  title: "SkillPolaris",
  description: "SkillPolaris",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className={cn("font-sans", geist.variable)}>
      <body>
        <div className="fixed inset-0 -z-10">
          <Sparkles background="#05070F" particleColor="#E4EAFB" />
        </div>
        <Navbar />
        <main className="mx-auto w-[min(100%-2rem,64rem)] py-8">{children}</main>
      </body>
    </html>
  );
}
