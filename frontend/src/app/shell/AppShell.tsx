import { NavLink, Outlet } from "react-router-dom";

import { useSession } from "../../lib/state/sessionStore";

export function AppShell() {
    const { session, logout } = useSession();

    const links = [
        { to: "/chat", label: "Chat", visible: true },
        { to: "/files", label: "File Manager", visible: true },
        {
            to: "/admin",
            label: "Admin",
            visible: Boolean(session?.permissions.canAccessAdmin),
        },
    ];

    return (
        <div className="app-shell">
            <aside className="side-nav">
                <h1>Knowledge Base</h1>
                <p className="muted">{session?.user.username}</p>
                <button type="button" onClick={() => void logout()}>
                    Logout
                </button>
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
