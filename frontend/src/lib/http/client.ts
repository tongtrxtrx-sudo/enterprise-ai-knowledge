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

const API_BASE = "/api";

function authHeaders(token: string): HeadersInit {
    return {
        Authorization: `Bearer ${token}`,
    };
}

export async function streamChat(
    token: string,
    payload: ChatRequest,
    onEvent: (event: StreamEvent) => void,
): Promise<void> {
    const response = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...authHeaders(token),
        },
        body: JSON.stringify(payload),
    });

    if (!response.ok || !response.body) {
        throw new Error("Chat stream failed");
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

    const response = await fetch(`${API_BASE}/uploads`, {
        method: "POST",
        headers: authHeaders(token),
        body: formData,
    });
    if (!response.ok) {
        throw new Error("Upload failed");
    }
    return (await response.json()) as UploadResponse;
}

export async function listVisibleFiles(token: string): Promise<VisibleFile[]> {
    const response = await fetch(`${API_BASE}/permissions/files`, {
        headers: authHeaders(token),
    });
    if (!response.ok) {
        throw new Error("File listing failed");
    }
    return (await response.json()) as VisibleFile[];
}

// Backend version list endpoint is not implemented yet; keep mock contract stable.
export async function listFileVersions(
    _token: string,
    fileId: number,
): Promise<FileVersionItem[]> {
    return [
        {
            version_number: 1,
            created_by: 1,
            created_at: "2026-03-03T14:00:00Z",
        },
        {
            version_number: 2,
            created_by: 1,
            created_at: "2026-03-03T15:00:00Z",
        },
    ].map((item) => ({ ...item, version_number: item.version_number + fileId % 2 }));
}

export async function startEditSession(
    token: string,
    fileId: number,
): Promise<EditStartResponse> {
    const response = await fetch(`${API_BASE}/files/${fileId}/edit/start`, {
        method: "POST",
        headers: authHeaders(token),
    });
    if (!response.ok) {
        throw new Error("Start edit failed");
    }
    return (await response.json()) as EditStartResponse;
}

export async function submitEditSaveCallback(
    token: string,
    fileId: number,
    sessionToken: string,
): Promise<void> {
    const response = await fetch(`${API_BASE}/files/${fileId}/edit/callback`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...authHeaders(token),
        },
        body: JSON.stringify({
            token: sessionToken,
            status: 6,
            content: "frontend-save-callback",
        }),
    });
    if (!response.ok) {
        throw new Error("Save callback failed");
    }
}

// Mocked admin data contracts. Backend endpoints are pending for these resources.
export async function listAdminUsers(_token: string): Promise<AdminUser[]> {
    return [
        {
            id: 1,
            username: "admin",
            role: "admin",
            department: "knowledge",
            status: "active",
        },
        {
            id: 2,
            username: "manager.ops",
            role: "dept_manager",
            department: "operations",
            status: "active",
        },
    ];
}

export async function listDepartments(_token: string): Promise<DepartmentState[]> {
    return [
        { name: "knowledge", manager_user_id: 1, member_count: 4 },
        { name: "operations", manager_user_id: 2, member_count: 6 },
    ];
}

export async function listFolderPermissions(token: string): Promise<FolderPermissionState[]> {
    const response = await fetch(`${API_BASE}/admin/folder-permissions`, {
        headers: authHeaders(token),
    });
    if (!response.ok) {
        throw new Error("Permission listing failed");
    }
    return (await response.json()) as FolderPermissionState[];
}

export async function listAuditStates(_token: string): Promise<AuditState[]> {
    return [
        {
            id: 201,
            actor_user_id: 1,
            action: "folder_permission_updated",
            target_type: "folder_permission",
            target_id: 10,
            created_at: "2026-03-03T15:22:00Z",
        },
        {
            id: 202,
            actor_user_id: 1,
            action: "upload_visibility_updated",
            target_type: "upload",
            target_id: 77,
            created_at: "2026-03-03T15:24:00Z",
        },
    ];
}
