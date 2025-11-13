import { useState, useEffect } from "react";
import axios from "axios";
import { API_BASE_URL } from "../config";

function UserManagement({ onSignOut }) {
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => { fetchUsers(); }, []);

  const fetchUsers = async () => {
    try {
      setIsLoading(true);
      const { data } = await axios.get(`${API_BASE_URL}/users`);
      if (data?.users) setUsers(data.users);
    } catch (err) {
      console.error("Fetch users error:", err);
      setError("Failed to fetch users. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="dashboard-page w-full">
      {/* Top bar */}
      <div className="w-full max-w-6xl mx-auto flex items-center justify-between mb-6">
        <h1 className="header-xl fade-up">User Management</h1>
        <div className="flex gap-3">
          <button onClick={fetchUsers} disabled={isLoading} className="btn btn-primary">
            {isLoading ? "Refreshing…" : "Refresh"}
          </button>
          <button onClick={onSignOut} className="btn btn-secondary">Sign Out</button>
        </div>
      </div>

      {/* Summary + errors */}
      <div className="w-full max-w-6xl mx-auto panel fade-up">
        <div className="grid sm:grid-cols-3 gap-4 mb-6">
          <div className="glass p-4 rounded-xl text-center">
            <div className="text-3xl font-extrabold text-blue-700">{users.length}</div>
            <div className="text-sm text-slate-600">Total Users</div>
          </div>
        </div>

        {error && (
          <div className="glass p-3 rounded-lg border border-red-200/70 text-red-700 text-sm mb-6">
            {error}
          </div>
        )}

        {/* Content */}
        {isLoading ? (
          <div className="text-center py-10 text-slate-600">Loading users…</div>
        ) : users.length === 0 ? (
          <div className="text-center py-10 text-slate-600">No users found.</div>
        ) : (
          <div className="stagger grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {users.map((user) => (
              <div key={user.UserId} className="glass p-6 rounded-2xl hover:-translate-y-1 transition">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-full bg-gradient-to-br from-blue-500 via-indigo-600 to-blue-700 text-white font-bold flex items-center justify-center">
                    {user.UserName?.charAt(0)?.toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <div className="font-extrabold text-slate-900 truncate">{user.UserName}</div>
                    <div className="text-xs text-slate-500">User ID: {user.UserId}</div>
                  </div>
                </div>

                <div className="mt-4">
                  <div className="text-xs text-slate-500 mb-1">Email</div>
                  <div className="text-sm font-mono bg-slate-50 border border-slate-200 rounded-lg p-2 break-words">
                    {user.UserEmail}
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between text-xs text-slate-600">
                  <span className="px-2 py-1 rounded-full bg-green-100 text-green-700 font-semibold">Active</span>
                  <span>
                    Since {new Date(user.CreatedAt).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: '2-digit' })}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default UserManagement;