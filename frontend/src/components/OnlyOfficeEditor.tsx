type OnlyOfficeEditorProps = {
    iframeUrl: string;
    fileId: number;
    canSave: boolean;
    onSave: () => Promise<void>;
};

export function OnlyOfficeEditor({ iframeUrl, fileId, canSave, onSave }: OnlyOfficeEditorProps) {
    return (
        <div className="card">
            <h3>ONLYOFFICE Session</h3>
            <p className="muted">Single-user edit session for file #{fileId}</p>
            <iframe
                title={`ONLYOFFICE-${fileId}`}
                src={iframeUrl}
                style={{ width: "100%", height: 360, border: "1px solid #d1d5db" }}
            />
            <div style={{ marginTop: 10 }}>
                <button type="button" onClick={() => void onSave()} disabled={!canSave}>
                    Save Callback
                </button>
            </div>
        </div>
    );
}
