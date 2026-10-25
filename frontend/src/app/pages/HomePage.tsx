import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";
import { BrainCircuit } from "lucide-react";

export function HomePage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background p-6">
      <Card className="w-full max-w-md">
        <CardHeader className="items-center text-center">
          <BrainCircuit className="mb-3 size-12 text-primary" />

          <CardTitle className="text-3xl font-bold">
            SmartDesk AI
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-4 text-center">
          <p className="text-muted-foreground">
            Sistema inteligente de gestão de chamados com IA.
          </p>

          <Button className="w-full">
            Começar
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}