import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

export type SessionRole = "user" | "dept_manager" | "admin";

export type SessionPermissions = {
    canUpload: boolean;
    canViewVersions: boolean;
    canEditFile: boolean;
    canAccessAdmin: boolean;
};

export type SessionUser = {
    id: number;
    username: string;
    role: SessionRole;
    department: string;
};

export type SessionState = {
    accessToken: string;
    user: SessionUser;
    permissions: SessionPermissions;
};

type SessionContextValue = {
    session: SessionState | null;
    setSession: (value: SessionState | null) => void;
};

export const defaultSession: SessionState = {
    accessToken: "demo-access-token",
    user: {
        id: 1,
        username: "demo.user",
        role: "admin",
        department: "knowledge",
    },
    permissions: {
        canUpload: true,
        canViewVersions: true,
        canEditFile: true,
        canAccessAdmin: true,
    },
};

const SessionContext = createContext<SessionContextValue | undefined>(undefined);

export function SessionProvider({
    children,
    initialSession = defaultSession,
}: {
    children: ReactNode;
    initialSession?: SessionState | null;
}) {
    const [session, setSession] = useState<SessionState | null>(initialSession);
    const value = useMemo(
        () => ({
            session,
            setSession,
        }),
        [session],
    );
    return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
    const ctx = useContext(SessionContext);
    if (!ctx) {
        throw new Error("useSession must be used inside SessionProvider");
    }
    return ctx;
}
