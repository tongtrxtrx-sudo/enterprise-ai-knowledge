import { FormEvent, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useI18n } from "../../i18n";
import { HttpError } from "../../lib/http/client";
import { useSession } from "../../lib/state/sessionStore";

type LoginLocationState = {
    from?: {
        pathname?: string;
    };
};

export function LoginPage() {
    const { session, login } = useSession();
    const { t } = useI18n();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [status, setStatus] = useState<"idle" | "submitting" | "error">("idle");
    const [errorMessage, setErrorMessage] = useState("");
    const location = useLocation();
    const state = location.state as LoginLocationState | undefined;
    const redirectTo = state?.from?.pathname || "/chat";

    if (session) {
        return <Navigate to={redirectTo} replace />;
    }

    async function onSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setStatus("submitting");
        setErrorMessage("");
        try {
            await login(username.trim(), password);
        } catch (error) {
            const httpError = error as HttpError;
            if (httpError?.status === 401) {
                setErrorMessage(t("login.error.invalidCredentials"));
            } else {
                setErrorMessage(t("login.error.generic"));
            }
            setStatus("error");
        }
    }

    return (
        <div className="card" style={{ maxWidth: 420, margin: "40px auto" }}>
            <h2>{t("login.title")}</h2>
            <p className="muted">{t("login.description")}</p>
            <form onSubmit={(event) => void onSubmit(event)}>
                <label htmlFor="username">{t("login.username")}</label>
                <input
                    id="username"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    autoComplete="username"
                />

                <label htmlFor="password">{t("login.password")}</label>
                <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    autoComplete="current-password"
                />

                <button type="submit" disabled={status === "submitting" || !username || !password}>
                    {status === "submitting" ? t("login.signingIn") : t("login.signIn")}
                </button>
            </form>
            {errorMessage ? <p role="alert">{errorMessage}</p> : null}
        </div>
    );
}
