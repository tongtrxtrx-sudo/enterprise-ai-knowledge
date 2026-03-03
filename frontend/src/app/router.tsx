import { Navigate, Outlet, type RouteObject } from "react-router-dom";

import { AdminPage } from "../features/admin/AdminPage";
import { ChatPage } from "../features/chat/ChatPage";
import { FileManagerPage } from "../features/files/FileManagerPage";
import { ForbiddenPage } from "../features/common/ForbiddenPage";
import { useSession } from "../lib/state/sessionStore";
import { AppShell } from "./shell/AppShell";

export function AuthGuard() {
    const { session } = useSession();
    if (!session) {
        return <ForbiddenPage />;
    }
    return <Outlet />;
}

export function AdminGuard() {
    const { session } = useSession();
    if (!session || !session.permissions.canAccessAdmin || session.user.role !== "admin") {
        return <ForbiddenPage />;
    }
    return <Outlet />;
}

export function createAppRoutes(): RouteObject[] {
    return [
        {
            path: "/",
            element: <AuthGuard />,
            children: [
                {
                    element: <AppShell />,
                    children: [
                    {
                        index: true,
                        element: <Navigate to="chat" replace />,
                    },
                    {
                        path: "chat",
                        element: <ChatPage />,
                    },
                    {
                        path: "files",
                        element: <FileManagerPage />,
                    },
                    {
                        path: "admin",
                        element: <AdminGuard />,
                            children: [
                                {
                                    index: true,
                                    element: <AdminPage />,
                                },
                            ],
                        },
                    ],
                },
            ],
        },
        {
            path: "/forbidden",
            element: <ForbiddenPage />,
        },
    ];
}
