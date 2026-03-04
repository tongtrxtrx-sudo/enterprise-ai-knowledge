import { FormEvent, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { HttpError } from "../../lib/http/client";
import { useSession } from "../../lib/state/sessionStore";

type LoginLocationState = {
    from?: {
        pathname?: string;
    };
};

export function LoginPage() {
    const { session, login } = useSession();
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
                setErrorMessage("Invalid username or password");
            } else {
                setErrorMessage("Login failed, please try again");
            }
            setStatus("error");
        }
    }

    return (
        <div className="card" style={{ maxWidth: 420, margin: "40px auto" }}>
            <h2>Login</h2>
            <p className="muted">Use your account to access the workspace.</p>
            <form onSubmit={(event) => void onSubmit(event)}>
                <label htmlFor="username">Username</label>
                <input
                    id="username"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    autoComplete="username"
                />

                <label htmlFor="password">Password</label>
                <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    autoComplete="current-password"
                />

                <button type="submit" disabled={status === "submitting" || !username || !password}>
                    {status === "submitting" ? "Signing in..." : "Sign in"}
                </button>
            </form>
            {errorMessage ? <p role="alert">{errorMessage}</p> : null}
        </div>
    );
}
