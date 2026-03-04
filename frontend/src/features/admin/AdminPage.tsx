import { useEffect, useState } from "react";

import { useI18n } from "../../i18n";
import {
    listAdminUsers,
    listAuditStates,
    listDepartments,
    listFolderPermissions,
    type AdminUser,
    type AuditState,
    type DepartmentState,
    type FolderPermissionState,
} from "../../lib/http/client";
import { useSession } from "../../lib/state/sessionStore";

export function AdminPage() {
    const { session } = useSession();
    const { t } = useI18n();
    const [users, setUsers] = useState<AdminUser[]>([]);
    const [departments, setDepartments] = useState<DepartmentState[]>([]);
    const [permissions, setPermissions] = useState<FolderPermissionState[]>([]);
    const [audits, setAudits] = useState<AuditState[]>([]);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        async function loadAdminState() {
            if (!session) {
                return;
            }
            setLoading(true);
            setError("");
            try {
                const [userRows, deptRows, permissionRows, auditRows] = await Promise.all([
                    listAdminUsers(session.accessToken),
                    listDepartments(session.accessToken),
                    listFolderPermissions(session.accessToken),
                    listAuditStates(session.accessToken),
                ]);
                setUsers(userRows);
                setDepartments(deptRows);
                setPermissions(permissionRows);
                setAudits(auditRows);
            } catch {
                setError(t("admin.error"));
                setUsers([]);
                setDepartments([]);
                setPermissions([]);
                setAudits([]);
            } finally {
                setLoading(false);
            }
        }
        void loadAdminState();
    }, [session, t]);

    return (
        <div>
            <div className="card">
                <h2>{t("admin.title")}</h2>
                <p className="muted">{t("admin.description")}</p>
                {loading ? <p>{t("admin.loading")}</p> : null}
                {error ? <p>{error}</p> : null}
            </div>

            <div className="grid">
                <div className="card">
                    <h3>{t("admin.users")}</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>{t("admin.id")}</th>
                                <th>{t("admin.username")}</th>
                                <th>{t("admin.role")}</th>
                                <th>{t("admin.department")}</th>
                                <th>{t("admin.status")}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {users.map((item) => (
                                <tr key={item.id}>
                                    <td>{item.id}</td>
                                    <td>{item.username}</td>
                                    <td>{item.role}</td>
                                    <td>{item.department}</td>
                                    <td>{item.status}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <div className="card">
                    <h3>{t("admin.departments")}</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>{t("admin.name")}</th>
                                <th>{t("admin.managerUserId")}</th>
                                <th>{t("admin.members")}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {departments.map((item) => (
                                <tr key={item.name}>
                                    <td>{item.name}</td>
                                    <td>{item.manager_user_id}</td>
                                    <td>{item.member_count}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            <div className="grid">
                <div className="card">
                    <h3>{t("admin.permissions")}</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>{t("admin.id")}</th>
                                <th>{t("admin.folder")}</th>
                                <th>{t("admin.granteeUserId")}</th>
                                <th>{t("admin.canEdit")}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {permissions.map((item) => (
                                <tr key={item.id}>
                                    <td>{item.id}</td>
                                    <td>{item.folder}</td>
                                    <td>{item.grantee_user_id}</td>
                                    <td>{item.can_edit ? t("admin.boolean.true") : t("admin.boolean.false")}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <div className="card">
                    <h3>{t("admin.audit")}</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>{t("admin.id")}</th>
                                <th>{t("admin.action")}</th>
                                <th>{t("admin.target")}</th>
                                <th>{t("admin.actor")}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {audits.map((item) => (
                                <tr key={item.id}>
                                    <td>{item.id}</td>
                                    <td>{item.action}</td>
                                    <td>
                                        {t("admin.targetFormat", {
                                            type: item.target_type,
                                            id: item.target_id ?? t("admin.targetUnknown"),
                                        })}
                                    </td>
                                    <td>{item.actor_user_id ?? t("admin.actorSystem")}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
