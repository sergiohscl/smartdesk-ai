import { Button } from "@/app/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/app/components/ui/card";

import { BrainCircuit, Activity } from "lucide-react";

export function HomePage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#111827] p-6">
      <Card className="w-full max-w-md border-gray-700 bg-[#1F2937] text-white shadow-2xl">
        <CardHeader className="items-center text-center">
          <BrainCircuit className="mb-3 size-12 text-blue-400" />

          <CardTitle className="text-3xl font-bold text-white">
            SmartDesk AI
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-6 text-center">
          <p className="text-gray-300">
            Sistema inteligente de gestão de chamados com IA.
          </p>

          <Button className="w-full bg-blue-600 text-white hover:bg-blue-700">
            Começar
          </Button>

          {/* Status da API */}
          <div className="rounded-lg border border-gray-600 bg-[#111827] p-4">
            <div className="mb-3 flex items-center justify-center gap-2">
              <Activity className="size-4 text-blue-400" />

              <h2 className="text-sm font-semibold text-white">
                Status do Sistema
              </h2>
            </div>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}