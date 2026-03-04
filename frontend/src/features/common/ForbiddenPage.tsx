import { useI18n } from "../../i18n";

export function ForbiddenPage() {
    const { t } = useI18n();

    return (
        <div className="card">
            <h2>{t("forbidden.title")}</h2>
            <p>{t("forbidden.description")}</p>
        </div>
    );
}
