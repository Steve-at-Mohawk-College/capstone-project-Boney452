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
      setError("");
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
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-blue-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <div>
              <h1 className="text-4xl font-bold text-slate-900 mb-2">User Management</h1>
              <p className="text-slate-600">Manage and view all registered users</p>
            </div>
            <div className="flex gap-3">
              <button 
                onClick={fetchUsers} 
                disabled={isLoading} 
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium shadow-md"
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin">⟳</span> Refreshing…
                  </span>
                ) : (
                  "🔄 Refresh"
                )}
              </button>
              <button 
                onClick={onSignOut} 
                className="px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 transition-colors font-medium shadow-md"
              >
                Sign Out
              </button>
            </div>
          </div>

          {/* Stats Card */}
          <div className="bg-white rounded-xl shadow-lg p-6 border border-slate-200">
            <div className="flex items-center gap-6">
              <div className="flex-1">
                <div className="text-sm text-slate-600 mb-1">Total Users</div>
                <div className="text-4xl font-bold text-blue-600">{users.length}</div>
              </div>
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-2xl font-bold">
                👥
              </div>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded-lg shadow-md">
            <div className="flex items-center gap-2">
              <span className="text-xl">⚠️</span>
              <span className="font-medium">{error}</span>
            </div>
          </div>
        )}

        {/* Users List */}
        {isLoading ? (
          <div className="bg-white rounded-xl shadow-lg p-12 text-center">
            <div className="inline-block animate-spin text-4xl text-blue-600 mb-4">⟳</div>
            <div className="text-slate-600 font-medium">Loading users…</div>
          </div>
        ) : users.length === 0 ? (
          <div className="bg-white rounded-xl shadow-lg p-12 text-center">
            <div className="text-6xl mb-4">👤</div>
            <div className="text-slate-600 font-medium text-lg">No users found</div>
            <div className="text-slate-500 text-sm mt-2">Users will appear here once they register</div>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden">
            {/* Table Header */}
            <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-4">
              <div className="grid grid-cols-12 gap-4 items-center font-semibold text-sm">
                <div className="col-span-1">Avatar</div>
                <div className="col-span-3">Username</div>
                <div className="col-span-4">Email</div>
                <div className="col-span-2">Status</div>
                <div className="col-span-2">Joined</div>
              </div>
            </div>

            {/* Users List */}
            <div className="divide-y divide-slate-200">
              {users.map((user, index) => (
                <div 
                  key={user.UserId} 
                  className="px-6 py-4 hover:bg-slate-50 transition-colors"
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <div className="grid grid-cols-12 gap-4 items-center">
                    {/* Avatar */}
                    <div className="col-span-1">
                      <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 via-indigo-600 to-blue-700 text-white font-bold flex items-center justify-center text-lg shadow-md">
                        {user.UserName?.charAt(0)?.toUpperCase() || "?"}
                      </div>
                    </div>

                    {/* Username */}
                    <div className="col-span-3">
                      <div className="font-bold text-slate-900">{user.UserName || "N/A"}</div>
                      <div className="text-xs text-slate-500">ID: {user.UserId}</div>
                    </div>

                    {/* Email */}
                    <div className="col-span-4">
                      <div className="text-sm text-slate-700 font-mono break-all">
                        {user.UserEmail || "N/A"}
                      </div>
                    </div>

                    {/* Status */}
                    <div className="col-span-2">
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800">
                        <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                        Active
                      </span>
                    </div>

                    {/* Joined Date */}
                    <div className="col-span-2">
                      <div className="text-sm text-slate-600">
                        {user.CreatedAt 
                          ? new Date(user.CreatedAt).toLocaleDateString('en-US', { 
                              year: 'numeric', 
                              month: 'short', 
                              day: 'numeric' 
                            })
                          : "N/A"
                        }
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default UserManagement;