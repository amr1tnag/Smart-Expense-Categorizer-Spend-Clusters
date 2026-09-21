import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Smart Expense Categorizer + Spend Clusters",
  description:
    "Naive Bayes labels each transaction; K-Means groups your spending behaviour.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
