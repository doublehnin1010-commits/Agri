import { BookOpenText, LogIn, Mail, ShieldCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { getApiErrorMessage } from "../api/client";
import { userFromToken, useAuthStore } from "../contexts/authStore";
import { login } from "../services/authService";

interface LoginForm {
  email: string;
  password: string;
}

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const setSession = useAuthStore((state) => state.setSession);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>();

  const onSubmit = async (values: LoginForm) => {
    try {
      const response = await login(values);
      const token = response.access_token ?? response.token;
      if (!token) throw new Error("Login response did not include a token");
      const user = response.user ?? userFromToken(token, response.role);
      setSession(token, user);
      toast.success("Welcome back");
      const requestedPath = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
      const redirectTo = user.role === "admin" ? "/admin" : requestedPath ?? "/dashboard";
      navigate(redirectTo, { replace: true });
    } catch (error) {
      toast.error(getApiErrorMessage(error));
    }
  };

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-soft">
      <div className="border-b border-slate-100 px-6 py-5">
        <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
          <BookOpenText className="h-5 w-5" aria-hidden="true" />
        </div>
        <h1 className="mt-4 text-2xl font-bold text-slate-950">Welcome back</h1>
        <p className="mt-2 text-sm leading-6 text-slate-500">
          Sign in to Burmese Proverbs Hub and continue your learning workspace.
        </p>
      </div>
      <form className="space-y-4 px-6 py-5" onSubmit={handleSubmit(onSubmit)}>
        <div className="space-y-2">
          <label className="form-label" htmlFor="email">Email</label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input id="email" type="email" autoComplete="email" className="form-input pl-9" {...register("email", { required: "Email is required" })} />
          </div>
          {errors.email ? <p className="text-sm text-red-600">{errors.email.message}</p> : null}
        </div>
        <div className="space-y-2">
          <label className="form-label" htmlFor="password">Password</label>
          <div className="relative">
            <ShieldCheck className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input id="password" type="password" autoComplete="current-password" className="form-input pl-9" {...register("password", { required: "Password is required" })} />
          </div>
          {errors.password ? <p className="text-sm text-red-600">{errors.password.message}</p> : null}
        </div>
        <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
          <LogIn className="h-4 w-4" aria-hidden="true" />
          {isSubmitting ? "Signing in..." : "Login"}
        </button>
      </form>
      <p className="border-t border-slate-100 px-6 py-4 text-center text-sm text-slate-500">
        New here? <Link to="/register" className="font-semibold text-brand-700 hover:underline">Create an account</Link>
      </p>
    </div>
  );
}
