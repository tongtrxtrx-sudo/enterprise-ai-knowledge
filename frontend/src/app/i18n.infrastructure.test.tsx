import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { createAppRoutes } from "./router";
import { defaultSession } from "../lib/state/sessionStore";
import { renderWithRouter } from "../test/utils";

describe("i18n infrastructure", () => {
    it("defaults to Chinese locale when no locale is stored", async () => {
        localStorage.removeItem("kb.locale");

        renderWithRouter(createAppRoutes(), {
            initialPath: "/login",
            session: null,
        });

        expect(await screen.findByRole("heading", { name: "登录" })).toBeInTheDocument();
    });

    it("uses stored English locale when configured", async () => {
        localStorage.setItem("kb.locale", "en");

        renderWithRouter(createAppRoutes(), {
            initialPath: "/chat",
            session: defaultSession,
        });

        expect(await screen.findByText("Knowledge Base")).toBeInTheDocument();
        expect(screen.getByRole("link", { name: "Chat" })).toBeInTheDocument();
    });
});
