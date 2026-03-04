import { useI18n } from "../i18n";

type OnlyOfficeEditorProps = {
    iframeUrl: string;
    fileId: number;
    canSave: boolean;
    onSave: () => Promise<void>;
};

export function OnlyOfficeEditor({ iframeUrl, fileId, canSave, onSave }: OnlyOfficeEditorProps) {
    const { t } = useI18n();

    return (
        <div className="card">
            <h3>{t("onlyoffice.title")}</h3>
            <p className="muted">{t("onlyoffice.description", { fileId })}</p>
            <iframe
                title={`ONLYOFFICE-${fileId}`}
                src={iframeUrl}
                style={{ width: "100%", height: 360, border: "1px solid #d1d5db" }}
            />
            <div style={{ marginTop: 10 }}>
                <button type="button" onClick={() => void onSave()} disabled={!canSave}>
                    {t("onlyoffice.saveCallback")}
                </button>
            </div>
        </div>
    );
}
