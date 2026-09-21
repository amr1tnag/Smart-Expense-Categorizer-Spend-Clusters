import type { Metadata } from "next";
import "@fontsource-variable/bricolage-grotesque/opsz.css";
import "@fontsource-variable/public-sans/index.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Expense categorizer",
  description:
    "Drop in a bank or UPI statement and see where the money went, what repeats every month, and which labels the model isn't sure about.",
};

// Runs before first paint so a saved theme choice never flashes the other one.
const themeInit = `try{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
