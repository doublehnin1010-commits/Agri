import { LogIn } from "lucide-react";
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
      const redirectTo = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/dashboard";
      navigate(redirectTo, { replace: true });
    } catch (error) {
      toast.error(getApiErrorMessage(error));
    }
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
      <h1 className="text-2xl font-bold text-slate-950">Login</h1>
      <p className="mt-2 text-sm leading-6 text-slate-500">Continue to your AI proverb tutor workspace.</p>
      <form className="mt-6 space-y-4" onSubmit={handleSubmit(onSubmit)}>
        <div className="space-y-2">
          <label className="form-label" htmlFor="email">Email</label>
          <input id="email" type="email" className="form-input" {...register("email", { required: "Email is required" })} />
          {errors.email ? <p className="text-sm text-red-600">{errors.email.message}</p> : null}
        </div>
        <div className="space-y-2">
          <label className="form-label" htmlFor="password">Password</label>
          <input id="password" type="password" className="form-input" {...register("password", { required: "Password is required" })} />
          {errors.password ? <p className="text-sm text-red-600">{errors.password.message}</p> : null}
        </div>
        <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
          <LogIn className="h-4 w-4" aria-hidden="true" />
          {isSubmitting ? "Signing in..." : "Login"}
        </button>
      </form>
      <p className="mt-5 text-center text-sm text-slate-500">
        New here? <Link to="/register" className="font-semibold text-brand-700 hover:underline">Create an account</Link>
      </p>
    </div>
  );
}
