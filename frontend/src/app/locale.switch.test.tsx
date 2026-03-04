import userEvent from "@testing-library/user-event";
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { createAppRoutes } from "./router";
import { defaultSession } from "../lib/state/sessionStore";
import { renderWithRouter } from "../test/utils";

describe("locale switch", () => {
    it("switches from Chinese to English labels", async () => {
        localStorage.removeItem("kb.locale");
        const user = userEvent.setup();

        renderWithRouter(createAppRoutes(), {
            initialPath: "/chat",
            session: defaultSession,
        });

        expect(await screen.findByRole("link", { name: "问答" })).toBeInTheDocument();

        await user.selectOptions(screen.getByLabelText("语言"), "en");

        expect(await screen.findByRole("link", { name: "Chat" })).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Logout" })).toBeInTheDocument();
    });

    it("persists selected locale in localStorage", async () => {
        localStorage.removeItem("kb.locale");
        const user = userEvent.setup();

        renderWithRouter(createAppRoutes(), {
            initialPath: "/chat",
            session: defaultSession,
        });

        await user.selectOptions(screen.getByLabelText("语言"), "en");

        expect(localStorage.getItem("kb.locale")).toBe("en");
    });
});
