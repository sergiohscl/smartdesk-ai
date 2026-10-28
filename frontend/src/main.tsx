import React from "react";
import ReactDOM from "react-dom/client";

import { QueryProvider } from "@/app/providers/QueryProvider";
import { AuthProvider } from "@/app/providers/AuthProvider";
import { AppRouterProvider } from "@/app/providers/AppRouterProvider";

import "./index.css";

ReactDOM.createRoot(
  document.getElementById("root")!,
).render(
  <React.StrictMode>
    <QueryProvider>
      <AuthProvider>
        <AppRouterProvider />
      </AuthProvider>
    </QueryProvider>
  </React.StrictMode>,
);
