import { NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../auth";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="glass sticky top-0 z-40 mt-4 rounded-2xl border px-4 py-3 shadow-card">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between">
        <button
          className="text-left font-display text-lg font-bold tracking-wide text-white"
          onClick={() => navigate("/dashboard")}
        >
          AI Cloud Cost Detective
        </button>
        <div className="flex items-center gap-4">
          <nav className="flex items-center gap-3 text-sm font-semibold">
            <NavLink
              to="/dashboard"
              className={({ isActive }) =>
                `rounded-md px-3 py-2 transition ${
                  isActive ? "bg-white/20 text-white" : "text-slate-200 hover:bg-white/10"
                }`
              }
            >
              Dashboard
            </NavLink>
            <NavLink
              to="/history"
              className={({ isActive }) =>
                `rounded-md px-3 py-2 transition ${
                  isActive ? "bg-white/20 text-white" : "text-slate-200 hover:bg-white/10"
                }`
              }
            >
              History
            </NavLink>
          </nav>
          <div className="hidden text-right text-xs text-slate-300 sm:block">
            <div>Signed in as</div>
            <div className="font-semibold text-slate-100">{user?.email}</div>
          </div>
          <button
            className="btn btn-muted"
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
