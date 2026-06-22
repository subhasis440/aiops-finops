import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../auth";

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await signup(email, password);
      navigate("/dashboard");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? "Signup failed. Please try another email.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-md items-center px-4">
      <section className="glass-strong w-full rounded-3xl p-8 shadow-card">
        <h1 className="font-display text-3xl font-bold text-white">Create Account</h1>
        <p className="subtle mt-2 text-sm">Start tracking cloud optimization opportunities.</p>

        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <div>
            <label className="mb-1 block text-sm font-semibold text-slate-100">Email</label>
            <input
              className="input-field"
              type="email"
              placeholder="name@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-semibold text-slate-100">Password</label>
            <input
              className="input-field"
              type="password"
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error ? <p className="text-sm text-red-300">{error}</p> : null}

          <button className="btn btn-brand w-full" type="submit" disabled={loading}>
            {loading ? "Creating account..." : "Sign up"}
          </button>
        </form>

        <p className="mt-5 text-sm text-slate-300">
          Already have an account?{" "}
          <Link className="font-semibold text-emerald-300 hover:text-emerald-200" to="/login">
            Login
          </Link>
        </p>
      </section>
    </main>
  );
}
