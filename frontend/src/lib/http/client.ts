export type Citation = {
    upload_id: number;
    chunk_index: number;
    score?: number;
};

export type StreamChunkEvent = {
    type: "chunk";
    delta: string;
    citations: Citation[];
    skill: string;
    cache_hit: boolean;
};

export type StreamDoneEvent = {
    type: "done";
};

export type StreamEvent = StreamChunkEvent | StreamDoneEvent;

export type ChatRequest = {
    query: string;
    folder?: string;
    public_query?: boolean;
};

export type VisibleFile = {
    id: number;
    folder: string;
    filename: string;
    owner_id: number;
    is_public: boolean;
    parse_status: string;
};

export type FileVersionItem = {
    version_number: number;
    created_by: number;
    created_at: string;
};

export type UploadResponse = {
    code: string;
    upload_id: number;
    folder: string;
    filename: string;
    version: number;
    checksum_sha256: string;
    object_key: string;
    parse_status: string;
};

export type EditStartResponse = {
    file_id: number;
    source_version: number;
    session_token: string;
    editor_config: {
        document?: {
            url?: string;
        };
    };
};

export type AdminUser = {
    id: number;
    username: string;
    role: string;
    department: string;
    status: "active" | "disabled";
};

export type DepartmentState = {
    name: string;
    manager_user_id: number;
    member_count: number;
};

export type FolderPermissionState = {
    id: number;
    folder: string;
    grantee_user_id: number;
    can_edit: boolean;
};

export type AuditState = {
    id: number;
    actor_user_id: number | null;
    action: string;
    target_type: string;
    target_id: number | null;
    created_at: string;
};

export type LoginRequest = {
    username: string;
    password: string;
};

export type TokenPairResponse = {
    access_token: string;
    refresh_token: string;
    token_type: string;
};

export type SessionBootstrapResponse = {
    user: {
        id: number;
        username: string;
        role: "user" | "dept_manager" | "admin";
        department: string;
    };
    permissions: {
        can_upload: boolean;
        can_view_versions: boolean;
        can_edit_file: boolean;
        can_access_admin: boolean;
    };
};

export class HttpError extends Error {
    status: number;

    constructor(message: string, status: number) {
        super(message);
        this.status = status;
    }
}

type AuthRuntime = {
    getAccessToken: () => string | null;
    refreshAccessToken: () => Promise<string | null>;
    onUnauthorized: () => void;
};

const API_BASE = "/api";
let authRuntime: AuthRuntime | null = null;

export function configureAuthRuntime(runtime: AuthRuntime | null): void {
    authRuntime = runtime;
}

function authHeaders(token: string): HeadersInit {
    return {
        Authorization: `Bearer ${token}`,
    };
}

function mergeHeaders(base: HeadersInit, extra?: HeadersInit): Headers {
    const headers = new Headers(base);
    if (!extra) {
        return headers;
    }
    const extraHeaders = new Headers(extra);
    extraHeaders.forEach((value, key) => {
        headers.set(key, value);
    });
    return headers;
}

function getErrorMessage(response: Response, fallback: string): string {
    if (response.status === 401) {
        return "Unauthorized";
    }
    return fallback;
}

async function requestWithAuth(
    path: string,
    init: RequestInit,
    providedToken?: string,
): Promise<Response> {
    const token = providedToken ?? authRuntime?.getAccessToken() ?? null;
    const firstHeaders = token
        ? mergeHeaders(authHeaders(token), init.headers)
        : mergeHeaders({}, init.headers);

    const firstResponse = await fetch(`${API_BASE}${path}`, {
        ...init,
        credentials: "same-origin",
        headers: firstHeaders,
    });

    if (firstResponse.status !== 401 || !authRuntime) {
        return firstResponse;
    }

    const refreshedToken = await authRuntime.refreshAccessToken();
    if (!refreshedToken) {
        authRuntime.onUnauthorized();
        return firstResponse;
    }

    const retryHeaders = mergeHeaders(authHeaders(refreshedToken), init.headers);
    const retryResponse = await fetch(`${API_BASE}${path}`, {
        ...init,
        credentials: "same-origin",
        headers: retryHeaders,
    });
    if (retryResponse.status === 401) {
        authRuntime.onUnauthorized();
    }
    return retryResponse;
}

async function readJsonOrThrow<T>(response: Response, errorMessage: string): Promise<T> {
    if (!response.ok) {
        throw new HttpError(getErrorMessage(response, errorMessage), response.status);
    }
    return (await response.json()) as T;
}

export async function loginWithPassword(payload: LoginRequest): Promise<TokenPairResponse> {
    const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        credentials: "same-origin",
        body: JSON.stringify(payload),
    });
    return await readJsonOrThrow<TokenPairResponse>(response, "Login failed");
}

export async function refreshAccessToken(): Promise<TokenPairResponse> {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        credentials: "same-origin",
    });
    return await readJsonOrThrow<TokenPairResponse>(response, "Refresh failed");
}

export async function fetchSessionProfile(
    token: string,
): Promise<SessionBootstrapResponse> {
    const response = await requestWithAuth("/auth/session", { method: "GET" }, token);
    return await readJsonOrThrow<SessionBootstrapResponse>(response, "Session bootstrap failed");
}

export async function logoutCurrentSession(): Promise<void> {
    const response = await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        credentials: "same-origin",
    });
    if (!response.ok && response.status !== 401) {
        throw new HttpError(getErrorMessage(response, "Logout failed"), response.status);
    }
}

export async function streamChat(
    token: string,
    payload: ChatRequest,
    onEvent: (event: StreamEvent) => void,
): Promise<void> {
    const response = await requestWithAuth(
        "/chat/stream",
        {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
        },
        token,
    );

    if (!response.ok || !response.body) {
        throw new HttpError(getErrorMessage(response, "Chat stream failed"), response.status);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
        const { done, value } = await reader.read();
        if (done) {
            break;
        }
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";

        for (const rawEvent of events) {
            const line = rawEvent
                .split("\n")
                .find((part) => part.trimStart().startsWith("data:"));
            if (!line) {
                continue;
            }
            const jsonText = line.replace(/^data:\s*/, "");
            const parsed = JSON.parse(jsonText) as StreamEvent;
            onEvent(parsed);
        }
    }
}

export async function uploadFile(
    token: string,
    folder: string,
    file: File,
): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("folder", folder);
    formData.append("filename", file.name);
    formData.append("file", file);

    const response = await requestWithAuth(
        "/uploads",
        {
            method: "POST",
            body: formData,
        },
        token,
    );
    return await readJsonOrThrow<UploadResponse>(response, "Upload failed");
}

export async function listVisibleFiles(token: string): Promise<VisibleFile[]> {
    const response = await requestWithAuth("/permissions/files", { method: "GET" }, token);
    return await readJsonOrThrow<VisibleFile[]>(response, "File listing failed");
}

export async function listFileVersions(
    token: string,
    fileId: number,
): Promise<FileVersionItem[]> {
    const response = await requestWithAuth(
        `/uploads/${fileId}/versions`,
        {
            method: "GET",
        },
        token,
    );
    return await readJsonOrThrow<FileVersionItem[]>(response, "Version listing failed");
}

export async function startEditSession(
    token: string,
    fileId: number,
): Promise<EditStartResponse> {
    const response = await requestWithAuth(
        `/files/${fileId}/edit/start`,
        {
            method: "POST",
        },
        token,
    );
    return await readJsonOrThrow<EditStartResponse>(response, "Start edit failed");
}

export async function submitEditSaveCallback(
    token: string,
    fileId: number,
    sessionToken: string,
): Promise<void> {
    const response = await requestWithAuth(
        `/files/${fileId}/edit/callback`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                token: sessionToken,
                status: 6,
                content: "frontend-save-callback",
            }),
        },
        token,
    );
    if (!response.ok) {
        throw new HttpError(getErrorMessage(response, "Save callback failed"), response.status);
    }
}

export async function listAdminUsers(token: string): Promise<AdminUser[]> {
    const response = await requestWithAuth(
        "/admin/users",
        {
            method: "GET",
        },
        token,
    );
    return await readJsonOrThrow<AdminUser[]>(response, "User listing failed");
}

export async function listDepartments(token: string): Promise<DepartmentState[]> {
    const response = await requestWithAuth(
        "/admin/departments",
        {
            method: "GET",
        },
        token,
    );
    return await readJsonOrThrow<DepartmentState[]>(response, "Department listing failed");
}

export async function listFolderPermissions(token: string): Promise<FolderPermissionState[]> {
    const response = await requestWithAuth(
        "/admin/folder-permissions",
        {
            method: "GET",
        },
        token,
    );
    return await readJsonOrThrow<FolderPermissionState[]>(response, "Permission listing failed");
}

export async function listAuditStates(token: string): Promise<AuditState[]> {
    const response = await requestWithAuth(
        "/admin/audit-states",
        {
            method: "GET",
        },
        token,
    );
    return await readJsonOrThrow<AuditState[]>(response, "Audit state listing failed");
}
