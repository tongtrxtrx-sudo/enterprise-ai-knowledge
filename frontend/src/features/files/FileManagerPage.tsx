import { useEffect, useMemo, useState } from "react";

import { OnlyOfficeEditor } from "../../components/OnlyOfficeEditor";
import { useI18n } from "../../i18n";
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
    const { t } = useI18n();
    const [folder, setFolder] = useState("/knowledge");
    const [files, setFiles] = useState<VisibleFile[]>([]);
    const [uploadStatus, setUploadStatus] = useState("idle");
    const [versionMap, setVersionMap] = useState<Record<number, FileVersionItem[]>>({});
    const [versionErrorMap, setVersionErrorMap] = useState<Record<number, string>>({});
    const [editingSession, setEditingSession] = useState<EditStartResponse | null>(null);
    const [loadingFiles, setLoadingFiles] = useState(false);
    const [loadError, setLoadError] = useState("");
    const [editError, setEditError] = useState("");

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
            setLoadingFiles(true);
            setLoadError("");
            try {
                const rows = await listVisibleFiles(session.accessToken);
                setFiles(rows);
            } catch {
                setLoadError(t("files.loadError"));
                setFiles([]);
            } finally {
                setLoadingFiles(false);
            }
        }
        void loadFiles();
    }, [session, t]);

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
        setVersionErrorMap((prev) => ({ ...prev, [fileId]: "" }));
        try {
            const rows = await listFileVersions(session.accessToken, fileId);
            setVersionMap((prev) => ({
                ...prev,
                [fileId]: rows,
            }));
        } catch {
            setVersionErrorMap((prev) => ({
                ...prev,
                [fileId]: t("files.versionLoadError"),
            }));
        }
    }

    async function onStartEdit(fileId: number) {
        if (!session) {
            return;
        }
        setEditError("");
        try {
            const edit = await startEditSession(session.accessToken, fileId);
            setEditingSession(edit);
        } catch {
            setEditError(t("files.editStartError"));
        }
    }

    async function onSaveEdit() {
        if (!session || !editingSession) {
            return;
        }
        setEditError("");
        try {
            await submitEditSaveCallback(
                session.accessToken,
                editingSession.file_id,
                editingSession.session_token,
            );
        } catch {
            setEditError(t("files.editSaveError"));
        }
    }

    const localizedUploadStatus = t(`files.uploadStatus.${uploadStatus}`);

    function localizeParseStatus(status: string) {
        const key = `files.parseStatus.${status}`;
        const translated = t(key);
        if (translated === key) {
            return t("files.parseStatus.unknown");
        }
        return translated;
    }

    return (
        <div>
            <div className="card">
                <h2>{t("files.title")}</h2>
                <p className="muted">{t("files.description")}</p>
                <label htmlFor="folder-input">{t("files.folder")}</label>
                <input
                    id="folder-input"
                    value={folder}
                    onChange={(event) => setFolder(event.target.value)}
                />
                <label htmlFor="file-input">{t("files.uploadFile")}</label>
                <input
                    id="file-input"
                    type="file"
                    disabled={!session?.permissions.canUpload}
                    onChange={(event) => onUpload(event.target.files?.[0] ?? null)}
                />
                <p data-testid="upload-status">
                    {t("files.uploadStatus", { status: localizedUploadStatus })}
                </p>
                {loadingFiles ? <p>{t("files.loading")}</p> : null}
                {loadError ? <p>{loadError}</p> : null}
                {!session?.permissions.canUpload && (
                    <p className="muted">{t("files.uploadPermissionRequired")}</p>
                )}
                {editError ? <p>{editError}</p> : null}
            </div>

            <div className="card">
                <h3>{t("files.folderTree")}</h3>
                {Object.entries(groupedFiles).map(([folderName, folderFiles]) => (
                    <div key={folderName} className="card">
                        <strong>{folderName}</strong>
                        <ul>
                            {folderFiles.map((item) => (
                                <li key={item.id}>
                                    <div>
                                        {t("files.fileRow", {
                                            filename: item.filename,
                                            status: localizeParseStatus(item.parse_status),
                                        })}
                                    </div>
                                    <div style={{ display: "flex", gap: 8, margin: "6px 0" }}>
                                        <button
                                            type="button"
                                            disabled={!session?.permissions.canViewVersions}
                                            onClick={() => void onLoadVersions(item.id)}
                                        >
                                            {t("files.versions")}
                                        </button>
                                        <button
                                            type="button"
                                            disabled={!session?.permissions.canEditFile}
                                            onClick={() => void onStartEdit(item.id)}
                                        >
                                            {t("files.edit")}
                                        </button>
                                    </div>
                                    {versionMap[item.id] && (
                                        <ul data-testid={`versions-${item.id}`}>
                                            {versionMap[item.id].map((version) => (
                                                <li key={`${item.id}-${version.version_number}`}>
                                                    {t("files.versionItem", {
                                                        version: version.version_number,
                                                        createdBy: version.created_by,
                                                    })}
                                                </li>
                                            ))}
                                        </ul>
                                    )}
                                    {versionErrorMap[item.id] ? <p>{versionErrorMap[item.id]}</p> : null}
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
