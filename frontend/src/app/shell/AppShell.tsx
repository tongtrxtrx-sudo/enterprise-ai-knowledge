import { NavLink, Outlet } from "react-router-dom";

import { useI18n } from "../../i18n";
import { useSession } from "../../lib/state/sessionStore";

export function AppShell() {
    const { session, logout } = useSession();
    const { locale, setLocale, t } = useI18n();

    const links = [
        { to: "/chat", label: t("app.nav.chat"), visible: true },
        { to: "/files", label: t("app.nav.files"), visible: true },
        {
            to: "/admin",
            label: t("app.nav.admin"),
            visible: Boolean(session?.permissions.canAccessAdmin),
        },
    ];

    return (
        <div className="app-shell">
            <aside className="side-nav">
                <h1>{t("app.title")}</h1>
                <p className="muted">{session?.user.username}</p>
                <button type="button" onClick={() => void logout()}>
                    {t("app.logout")}
                </button>
                <label htmlFor="locale-switch">{t("app.language")}</label>
                <select
                    id="locale-switch"
                    value={locale}
                    onChange={(event) => setLocale(event.target.value as "zh-CN" | "en")}
                >
                    <option value="zh-CN">{t("app.language.zh-CN")}</option>
                    <option value="en">{t("app.language.en")}</option>
                </select>
                {links
                    .filter((item) => item.visible)
                    .map((item) => (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            className={({ isActive }) => (isActive ? "active" : "")}
                        >
                            {item.label}
                        </NavLink>
                    ))}
            </aside>
            <main className="content">
                <Outlet />
            </main>
        </div>
    );
}
