
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import axios from "axios";
import {
  UserPlus,
  UserRound,
  Mail,
  LockKeyhole,
  LoaderCircle,
} from "lucide-react";

import { useRegister } from "@/hooks/useAuth";
import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/app/components/ui/card";

export function RegisterPage() {
  const navigate = useNavigate();
  const registerMutation = useRegister();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const normalizedName = name.trim();
    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedName || !normalizedEmail || !password) {
      setError("Preencha todos os campos obrigatórios.");
      return;
    }

    if (password.length < 8) {
      setError("A senha deve conter pelo menos 8 caracteres.");
      return;
    }

    if (password !== confirmPassword) {
      setError("As senhas não coincidem.");
      return;
    }

    try {
      await registerMutation.mutateAsync({
        name: normalizedName,
        email: normalizedEmail,
        password,
      });

      await navigate({ to: "/login" });
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const status = err.response?.status;
        const detail = err.response?.data?.detail;

        if (status === 409) {
          setError("Este e-mail já está cadastrado.");
        } else if (status === 422) {
          setError(
            typeof detail === "string"
              ? detail
              : "Verifique os dados informados.",
          );
        } else if (!err.response) {
          setError("Não foi possível conectar ao servidor.");
        } else {
          setError("Não foi possível realizar o cadastro.");
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
            <UserPlus className="h-7 w-7" />
          </div>

          <h1 className="text-3xl font-bold tracking-tight text-white">
            SmartDesk AI
          </h1>

          <p className="text-sm text-slate-400">
            Crie sua conta para começar a utilizar a plataforma.
          </p>
        </div>

        <Card className="border border-slate-800 bg-slate-900 text-white shadow-2xl ring-0">
          <CardHeader className="space-y-2">
            <CardTitle className="text-xl font-semibold text-white">
              Criar conta
            </CardTitle>

            <CardDescription className="text-slate-400">
              Preencha os dados abaixo para se cadastrar.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <label htmlFor="name" className="text-sm font-medium text-slate-200">
                  Nome completo
                </label>

                <div className="relative">
                  <UserRound className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400" />

                  <Input
                    id="name"
                    type="text"
                    autoComplete="name"
                    placeholder="Seu nome completo"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    required
                    disabled={registerMutation.isPending}
                    className="h-11 border-slate-700 bg-slate-950 pl-10 text-white placeholder:text-slate-500"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium text-slate-200">
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
                    disabled={registerMutation.isPending}
                    className="h-11 border-slate-700 bg-slate-950 pl-10 text-white placeholder:text-slate-500"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-medium text-slate-200">
                  Senha
                </label>

                <div className="relative">
                  <LockKeyhole className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400" />

                  <Input
                    id="password"
                    type="password"
                    autoComplete="new-password"
                    placeholder="Mínimo de 8 caracteres"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    minLength={8}
                    required
                    disabled={registerMutation.isPending}
                    className="h-11 border-slate-700 bg-slate-950 pl-10 text-white placeholder:text-slate-500"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="confirmPassword"
                  className="text-sm font-medium text-slate-200"
                >
                  Confirmar senha
                </label>

                <div className="relative">
                  <LockKeyhole className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400" />

                  <Input
                    id="confirmPassword"
                    type="password"
                    autoComplete="new-password"
                    placeholder="Digite a senha novamente"
                    value={confirmPassword}
                    onChange={(event) =>
                      setConfirmPassword(event.target.value)
                    }
                    required
                    disabled={registerMutation.isPending}
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
                disabled={registerMutation.isPending}
                className="h-11 w-full bg-blue-600 font-semibold text-white hover:bg-blue-500"
              >
                {registerMutation.isPending ? (
                  <>
                    <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                    Criando conta...
                  </>
                ) : (
                  <>
                    <UserPlus className="mr-2 h-4 w-4" />
                    Criar conta
                  </>
                )}
              </Button>

              <p className="text-center text-sm text-slate-400">
                Já possui uma conta?{" "}
                <Link
                  to="/login"
                  className="font-medium text-blue-400 hover:text-blue-300"
                >
                  Fazer login
                </Link>
              </p>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
