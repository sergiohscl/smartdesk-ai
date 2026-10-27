import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "@tanstack/react-router";

import { QueryProvider } from "@/app/providers/QueryProvider";
import { router } from "@/app/router";

import "./index.css";
import { AuthProvider } from "./app/providers/AuthProvider";

ReactDOM.createRoot(
  document.getElementById("root")!,
).render(
  <React.StrictMode>
    <QueryProvider>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryProvider>
  </React.StrictMode>,
);