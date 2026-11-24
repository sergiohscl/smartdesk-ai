import {
  Activity,
  Bell,
  ChartNoAxesCombined,
  ExternalLink,
  Server,
  ShieldAlert,
  Timer,
} from "lucide-react";

import { DashboardLayout } from "@/app/components/DashboardLayout/DashboardLayout";

function getGrafanaDashboardUrl(): string | null {
  const value = import.meta.env.VITE_GRAFANA_DASHBOARD_URL?.trim();

  if (!value) {
    return null;
  }

  try {
    const url = new URL(value);

    if (
      url.protocol !== "http:" &&
      url.protocol !== "https:"
    ) {
      return null;
    }

    if (url.username || url.password) {
      return null;
    }

    return url.href;
  } catch {
    return null;
  }
}

const monitoringRules = [
  {
    name: "SmartDeskBackendDown",
    title: "Disponibilidade do backend",
    description:
      "Detecta indisponibilidade do backend por pelo menos 2 minutos.",
    severity: "critical",
    icon: Server,
  },
  {
    name: "SmartDeskHighHTTP5xxRate",
    title: "Taxa de erros HTTP 5xx",
    description:
      "Detecta uma taxa de erros superior a 5% durante 5 minutos, com tráfego suficiente.",
    severity: "warning",
    icon: ShieldAlert,
  },
  {
    name: "SmartDeskHighHTTPLatency",
    title: "Latência HTTP P95",
    description:
      "Detecta latência P95 superior a 1 segundo durante 5 minutos, com tráfego suficiente.",
    severity: "warning",
    icon: Timer,
  },
] as const;

export function MonitoringPage() {
  const grafanaUrl = getGrafanaDashboardUrl();

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <div className="flex items-center gap-3">
            <Activity
              size={28}
              className="text-blue-500"
              aria-hidden="true"
            />

            <h2 className="text-2xl font-bold text-white">
              Central de Monitoramento
            </h2>
          </div>

          <p className="mt-2 text-sm text-slate-400">
            Acompanhe a disponibilidade, o desempenho e
            os alertas do SmartDesk AI.
          </p>
        </div>

        <section
          aria-labelledby="grafana-title"
          className="rounded-xl border border-slate-800 bg-slate-900 p-6"
        >
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="rounded-xl bg-orange-500/10 p-3">
                <ChartNoAxesCombined
                  size={28}
                  className="text-orange-400"
                  aria-hidden="true"
                />
              </div>

              <div>
                <h3
                  id="grafana-title"
                  className="text-lg font-semibold text-white"
                >
                  Dashboard Grafana
                </h3>

                <p className="mt-1 text-sm text-slate-400">
                  Visualize métricas e indicadores de
                  desempenho do sistema.
                </p>
              </div>
            </div>

            {grafanaUrl ? (
              <a
                href={grafanaUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
              >
                Abrir Grafana

                <ExternalLink
                  size={16}
                  aria-hidden="true"
                />
              </a>
            ) : (
              <span
                role="status"
                className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2.5 text-sm text-amber-300"
              >
                URL do Grafana não configurada ou inválida
              </span>
            )}
          </div>
        </section>

        <section aria-labelledby="alerts-title">
          <div className="mb-4 flex items-center gap-2">
            <Bell
              size={22}
              className="text-blue-400"
              aria-hidden="true"
            />

            <h3
              id="alerts-title"
              className="text-lg font-semibold text-white"
            >
              Alertas do sistema
            </h3>
          </div>

          <div
            role="status"
            className="mb-4 rounded-lg border border-blue-500/20 bg-blue-500/5 p-4 text-sm text-slate-300"
          >
            As regras previstas são apresentadas abaixo.
            A consulta dos estados em tempo real será
            disponibilizada após a integração com a API
            de monitoramento.
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            {monitoringRules.map((rule) => {
              const Icon = rule.icon;

              return (
                <article
                  key={rule.name}
                  className="rounded-xl border border-slate-800 bg-slate-900 p-5"
                >
                  <div className="mb-4 flex items-center justify-between gap-2">
                    <div className="rounded-lg bg-slate-800 p-3">
                      <Icon
                        size={24}
                        className="text-blue-400"
                        aria-hidden="true"
                      />
                    </div>

                    <span
                      className={
                        rule.severity === "critical"
                          ? "rounded-full bg-red-500/10 px-3 py-1 text-xs font-medium text-red-400"
                          : "rounded-full bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-400"
                      }
                    >
                      {rule.severity === "critical"
                        ? "Crítico"
                        : "Atenção"}
                    </span>
                  </div>

                  <h4 className="font-semibold text-white">
                    {rule.title}
                  </h4>

                  <p className="mt-2 text-sm text-slate-400">
                    {rule.description}
                  </p>

                  <div className="mt-4 border-t border-slate-800 pt-4">
                    <span className="text-xs text-slate-400">
                      Estado: não consultado
                    </span>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </div>
    </DashboardLayout>
  );
}
