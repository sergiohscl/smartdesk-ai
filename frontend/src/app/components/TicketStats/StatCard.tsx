import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: number;
  icon: LucideIcon;
  iconColor: string;
}

export function StatCard({
  title,
  value,
  icon: Icon,
  iconColor,
}: StatCardProps) {
  return (
    <div className="rounded-xl border border-gray-700 bg-gray-800 p-5 transition-colors hover:border-gray-600">
      <div className="mb-4 flex items-center justify-between">
        <div className="rounded-lg bg-gray-900 p-3">
          <Icon
            className="h-6 w-6"
            style={{ color: iconColor }}
            aria-hidden="true"
          />
        </div>
      </div>

      <div className="space-y-1">
        <p className="text-3xl font-bold text-white">
          {value.toLocaleString("pt-BR")}
        </p>

        <h3 className="text-sm font-medium text-gray-400">
          {title}
        </h3>
      </div>
    </div>
  );
}
