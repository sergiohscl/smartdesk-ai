import { useState } from "react";

import type { ReactNode } from "react";

import { DashboardSidebar } from "./DashboardSidebar";
import { DashboardHeader } from "./DashboardHeader";

interface DashboardLayoutProps {
  children: ReactNode;
}

export function DashboardLayout({
  children,
}: DashboardLayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <DashboardSidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      <div className="min-h-screen md:pl-64">
        <DashboardHeader
          onOpenMenu={() => setIsSidebarOpen(true)}
        />

        <main className="p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}