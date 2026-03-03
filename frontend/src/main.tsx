import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider, createBrowserRouter } from "react-router-dom";

import { createAppRoutes } from "./app/router";
import { SessionProvider } from "./lib/state/sessionStore";
import "./styles.css";

export const runtimeInfo = {
    serviceName: "kb-frontend",
    version: "2.1.0",
};

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
        <SessionProvider>
            <RouterProvider router={createBrowserRouter(createAppRoutes())} />
        </SessionProvider>
    </React.StrictMode>,
);
