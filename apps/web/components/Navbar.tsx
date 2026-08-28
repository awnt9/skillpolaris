"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Home" },
  { href: "/orientar", label: "Orientar" },
  { href: "/docs", label: "Docs" },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-4 z-50 mx-auto w-[min(100%-2rem,64rem)]">
      <nav className="clay flex items-center justify-between rounded-[2rem] px-6 py-3">
        <span className="flex items-center gap-2 text-lg font-semibold tracking-tight text-primary">
          <Image src="/logo.svg" alt="" width={48} height={48} />
          SkillPolaris
        </span>
        <ul className="flex items-center gap-2">
          {links.map((link) => {
            const isActive =
              link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);

            return (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className={`rounded-2xl px-4 py-2 text-sm font-medium ${
                    isActive ? "nav-link-active" : "nav-link"
                  }`}
                >
                  {link.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </header>
  );
}
