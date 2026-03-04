import { useEffect, useState } from "react";

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
                setError("Failed to load admin state");
                setUsers([]);
                setDepartments([]);
                setPermissions([]);
                setAudits([]);
            } finally {
                setLoading(false);
            }
        }
        void loadAdminState();
    }, [session]);

    return (
        <div>
            <div className="card">
                <h2>Admin Console</h2>
                <p className="muted">Admin-only states for users, departments, permissions, and audit.</p>
                {loading ? <p>Loading admin state...</p> : null}
                {error ? <p>{error}</p> : null}
            </div>

            <div className="grid">
                <div className="card">
                    <h3>Users</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Username</th>
                                <th>Role</th>
                                <th>Department</th>
                                <th>Status</th>
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
                    <h3>Departments</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Manager User ID</th>
                                <th>Members</th>
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
                    <h3>Permissions</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Folder</th>
                                <th>Grantee User ID</th>
                                <th>Can Edit</th>
                            </tr>
                        </thead>
                        <tbody>
                            {permissions.map((item) => (
                                <tr key={item.id}>
                                    <td>{item.id}</td>
                                    <td>{item.folder}</td>
                                    <td>{item.grantee_user_id}</td>
                                    <td>{item.can_edit ? "true" : "false"}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <div className="card">
                    <h3>Audit</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Action</th>
                                <th>Target</th>
                                <th>Actor</th>
                            </tr>
                        </thead>
                        <tbody>
                            {audits.map((item) => (
                                <tr key={item.id}>
                                    <td>{item.id}</td>
                                    <td>{item.action}</td>
                                    <td>
                                        {item.target_type}#{item.target_id ?? "-"}
                                    </td>
                                    <td>{item.actor_user_id ?? "system"}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
