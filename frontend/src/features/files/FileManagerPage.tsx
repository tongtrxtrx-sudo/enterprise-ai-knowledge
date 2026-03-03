import { useEffect, useMemo, useState } from "react";

import { OnlyOfficeEditor } from "../../components/OnlyOfficeEditor";
import {
    listFileVersions,
    listVisibleFiles,
    startEditSession,
    submitEditSaveCallback,
    uploadFile,
    type EditStartResponse,
    type FileVersionItem,
    type VisibleFile,
} from "../../lib/http/client";
import { useSession } from "../../lib/state/sessionStore";

export function FileManagerPage() {
    const { session } = useSession();
    const [folder, setFolder] = useState("/knowledge");
    const [files, setFiles] = useState<VisibleFile[]>([]);
    const [uploadStatus, setUploadStatus] = useState("idle");
    const [versionMap, setVersionMap] = useState<Record<number, FileVersionItem[]>>({});
    const [editingSession, setEditingSession] = useState<EditStartResponse | null>(null);

    const groupedFiles = useMemo(() => {
        return files.reduce<Record<string, VisibleFile[]>>((acc, item) => {
            const key = item.folder;
            if (!acc[key]) {
                acc[key] = [];
            }
            acc[key].push(item);
            return acc;
        }, {});
    }, [files]);

    useEffect(() => {
        async function loadFiles() {
            if (!session) {
                return;
            }
            const rows = await listVisibleFiles(session.accessToken);
            setFiles(rows);
        }
        void loadFiles();
    }, [session]);

    async function onUpload(file: File | null) {
        if (!file || !session) {
            return;
        }
        setUploadStatus("uploading");
        try {
            await uploadFile(session.accessToken, folder, file);
            const rows = await listVisibleFiles(session.accessToken);
            setFiles(rows);
            setUploadStatus("done");
        } catch {
            setUploadStatus("error");
        }
    }

    async function onLoadVersions(fileId: number) {
        if (!session) {
            return;
        }
        const rows = await listFileVersions(session.accessToken, fileId);
        setVersionMap((prev) => ({
            ...prev,
            [fileId]: rows,
        }));
    }

    async function onStartEdit(fileId: number) {
        if (!session) {
            return;
        }
        const edit = await startEditSession(session.accessToken, fileId);
        setEditingSession(edit);
    }

    async function onSaveEdit() {
        if (!session || !editingSession) {
            return;
        }
        await submitEditSaveCallback(
            session.accessToken,
            editingSession.file_id,
            editingSession.session_token,
        );
    }

    return (
        <div>
            <div className="card">
                <h2>File Manager</h2>
                <p className="muted">Upload, browse tree, and view versions with permission controls.</p>
                <label htmlFor="folder-input">Folder</label>
                <input
                    id="folder-input"
                    value={folder}
                    onChange={(event) => setFolder(event.target.value)}
                />
                <label htmlFor="file-input">Upload File</label>
                <input
                    id="file-input"
                    type="file"
                    disabled={!session?.permissions.canUpload}
                    onChange={(event) => onUpload(event.target.files?.[0] ?? null)}
                />
                <p data-testid="upload-status">Upload status: {uploadStatus}</p>
                {!session?.permissions.canUpload && (
                    <p className="muted">Upload permission is required.</p>
                )}
            </div>

            <div className="card">
                <h3>Folder Tree</h3>
                {Object.entries(groupedFiles).map(([folderName, folderFiles]) => (
                    <div key={folderName} className="card">
                        <strong>{folderName}</strong>
                        <ul>
                            {folderFiles.map((item) => (
                                <li key={item.id}>
                                    <div>
                                        {item.filename} - {item.parse_status}
                                    </div>
                                    <div style={{ display: "flex", gap: 8, margin: "6px 0" }}>
                                        <button
                                            type="button"
                                            disabled={!session?.permissions.canViewVersions}
                                            onClick={() => void onLoadVersions(item.id)}
                                        >
                                            Versions
                                        </button>
                                        <button
                                            type="button"
                                            disabled={!session?.permissions.canEditFile}
                                            onClick={() => void onStartEdit(item.id)}
                                        >
                                            Edit
                                        </button>
                                    </div>
                                    {versionMap[item.id] && (
                                        <ul data-testid={`versions-${item.id}`}>
                                            {versionMap[item.id].map((version) => (
                                                <li key={`${item.id}-${version.version_number}`}>
                                                    v{version.version_number} by #{version.created_by}
                                                </li>
                                            ))}
                                        </ul>
                                    )}
                                </li>
                            ))}
                        </ul>
                    </div>
                ))}
            </div>

            {editingSession && (
                <OnlyOfficeEditor
                    fileId={editingSession.file_id}
                    iframeUrl={editingSession.editor_config.document?.url ?? "about:blank"}
                    canSave={Boolean(session?.permissions.canEditFile)}
                    onSave={onSaveEdit}
                />
            )}
        </div>
    );
}
