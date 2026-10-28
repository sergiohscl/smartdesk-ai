
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import axios from "axios";
import { LogIn, LoaderCircle, LockKeyhole, Mail } from "lucide-react";

import { useAuth } from "@/app/providers/AuthProvider";
import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/app/components/ui/card";

export function LoginPage() {
  const navigate = useNavigate();
  const { login, isLoading } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!email.trim() || !password) {
      setError("Informe seu e-mail e sua senha.");
      return;
    }

    try {
      await login({
        email: email.trim(),
        password,
      });

      await navigate({ to: "/" });
    } catch (err) {
      if (axios.isAxiosError(err)) {
        if (err.response?.status === 401) {
          setError("E-mail ou senha inválidos.");
        } else {
          setError(
            "Não foi possível realizar o login. Tente novamente.",
          );
        }
      } else {
        setError("Ocorreu um erro inesperado.");
      }
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-10">
      <div className="w-full max-w-md space-y-8">
        <div className="space-y-3 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-lg shadow-blue-600/20">
            <LockKeyhole className="h-7 w-7" />
          </div>

          <h1 className="text-3xl font-bold tracking-tight text-white">
            SmartDesk AI
          </h1>

          <p className="text-sm text-slate-400">
            Entre na sua conta para acessar a plataforma.
          </p>
        </div>

        <Card className="border border-slate-800 bg-slate-900 text-white shadow-2xl ring-0">
          <CardHeader className="space-y-2">
            <CardTitle className="text-xl font-semibold text-white">
              Entrar na plataforma
            </CardTitle>

            <CardDescription className="text-slate-400">
              Informe suas credenciais para continuar.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <label
                  htmlFor="email"
                  className="text-sm font-medium text-slate-200"
                >
                  E-mail
                </label>

                <div className="relative">
                  <Mail className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400" />

                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    placeholder="seu@email.com"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                    disabled={isLoading}
                    className="h-11 border-slate-700 bg-slate-950 pl-10 text-white placeholder:text-slate-500"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="password"
                  className="text-sm font-medium text-slate-200"
                >
                  Senha
                </label>

                <div className="relative">
                  <LockKeyhole className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400" />

                  <Input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    placeholder="Digite sua senha"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    disabled={isLoading}
                    className="h-11 border-slate-700 bg-slate-950 pl-10 text-white placeholder:text-slate-500"
                  />
                </div>
              </div>

              {error && (
                <div
                  role="alert"
                  className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400"
                >
                  {error}
                </div>
              )}

              <Button
                type="submit"
                disabled={isLoading}
                className="h-11 w-full bg-blue-600 font-semibold text-white hover:bg-blue-500"
              >
                {isLoading ? (
                  <>
                    <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                    Entrando...
                  </>
                ) : (
                  <>
                    <LogIn className="mr-2 h-4 w-4" />
                    Entrar
                  </>
                )}
              </Button>

              <p className="text-center text-sm text-slate-400">
                Ainda não possui uma conta?{" "}
                <Link
                  to="/register"
                  className="font-medium text-blue-400 hover:text-blue-300"
                >
                  Cadastre-se
                </Link>
              </p>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
