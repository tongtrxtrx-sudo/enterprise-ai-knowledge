import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
    type ReactNode,
} from "react";

import {
    HttpError,
    configureAuthRuntime,
    fetchSessionProfile,
    loginWithPassword,
    logoutCurrentSession,
    refreshAccessToken,
} from "../http/client";

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
    isBootstrapping: boolean;
    setSession: (value: SessionState | null) => void;
    login: (username: string, password: string) => Promise<void>;
    logout: () => Promise<void>;
    refreshSession: () => Promise<string | null>;
};

const ACCESS_TOKEN_STORAGE_KEY = "kb_access_token";

export const defaultSession: SessionState = {
    accessToken: "test-access-token",
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
    initialSession = null,
}: {
    children: ReactNode;
    initialSession?: SessionState | null;
}) {
    const [session, setSession] = useState<SessionState | null>(initialSession);
    const [isBootstrapping, setIsBootstrapping] = useState(initialSession === null);

    const clearSession = useCallback(() => {
        localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
        setSession(null);
    }, []);

    const applyAccessToken = useCallback(async (token: string): Promise<void> => {
        const profile = await fetchSessionProfile(token);
        localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
        setSession({
            accessToken: token,
            user: {
                id: profile.user.id,
                username: profile.user.username,
                role: profile.user.role,
                department: profile.user.department,
            },
            permissions: {
                canUpload: profile.permissions.can_upload,
                canViewVersions: profile.permissions.can_view_versions,
                canEditFile: profile.permissions.can_edit_file,
                canAccessAdmin: profile.permissions.can_access_admin,
            },
        });
    }, []);

    const refreshSession = useCallback(async (): Promise<string | null> => {
        try {
            const refreshed = await refreshAccessToken();
            await applyAccessToken(refreshed.access_token);
            return refreshed.access_token;
        } catch {
            clearSession();
            return null;
        }
    }, [applyAccessToken, clearSession]);

    const login = useCallback(
        async (username: string, password: string): Promise<void> => {
            const tokenPair = await loginWithPassword({ username, password });
            await applyAccessToken(tokenPair.access_token);
        },
        [applyAccessToken],
    );

    const logout = useCallback(async (): Promise<void> => {
        try {
            await logoutCurrentSession();
        } finally {
            clearSession();
        }
    }, [clearSession]);

    useEffect(() => {
        if (initialSession !== null) {
            setIsBootstrapping(false);
            return;
        }

        let active = true;
        async function bootstrapFromStorage() {
            const token = localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
            if (!token) {
                if (active) {
                    clearSession();
                    setIsBootstrapping(false);
                }
                return;
            }

            try {
                await applyAccessToken(token);
            } catch (error) {
                const httpError = error as HttpError;
                if (httpError?.status === 401) {
                    await refreshSession();
                } else {
                    clearSession();
                }
            } finally {
                if (active) {
                    setIsBootstrapping(false);
                }
            }
        }

        void bootstrapFromStorage();
        return () => {
            active = false;
        };
    }, [applyAccessToken, clearSession, initialSession, refreshSession]);

    useEffect(() => {
        configureAuthRuntime({
            getAccessToken: () => session?.accessToken ?? null,
            refreshAccessToken: refreshSession,
            onUnauthorized: clearSession,
        });
        return () => {
            configureAuthRuntime(null);
        };
    }, [clearSession, refreshSession, session?.accessToken]);

    const value = useMemo(
        () => ({
            session,
            setSession,
            isBootstrapping,
            login,
            logout,
            refreshSession,
        }),
        [isBootstrapping, login, logout, refreshSession, session],
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
