import { render } from "@testing-library/react";
import { RouterProvider, createMemoryRouter, type RouteObject } from "react-router-dom";

import { SessionProvider, defaultSession, type SessionState } from "../lib/state/sessionStore";

export function renderWithRouter(
    routes: RouteObject[],
    {
        initialPath = "/",
        session = defaultSession,
    }: {
        initialPath?: string;
        session?: SessionState | null;
    } = {},
) {
    const router = createMemoryRouter(routes, {
        initialEntries: [initialPath],
    });

    return render(
        <SessionProvider initialSession={session}>
            <RouterProvider router={router} />
        </SessionProvider>,
    );
}
