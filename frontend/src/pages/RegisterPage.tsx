import { Mail, ShieldCheck, UserRound, UserPlus } from "lucide-react";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import { Link, useNavigate } from "react-router-dom";
import { getApiErrorMessage } from "../api/client";
import { register as registerUser } from "../services/authService";
import type { RegisterPayload } from "../types";

export function RegisterPage() {
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterPayload>();

  const onSubmit = async (values: RegisterPayload) => {
    try {
      await registerUser(values);
      toast.success("Registration successful. Please log in.");
      navigate("/login");
    } catch (error) {
      toast.error(getApiErrorMessage(error));
    }
  };

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-soft">
      <div className="border-b border-slate-100 px-6 py-5">
        <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
          <UserPlus className="h-5 w-5" aria-hidden="true" />
        </div>
        <h1 className="mt-4 text-2xl font-bold text-slate-950">Create your account</h1>
        <p className="mt-2 text-sm leading-6 text-slate-500">
          Join Burmese Proverbs Hub for guided proverb explanations and classroom-ready examples.
        </p>
      </div>
      <form className="space-y-4 px-6 py-5" onSubmit={handleSubmit(onSubmit)}>
        <div className="space-y-2">
          <label className="form-label" htmlFor="username">Username</label>
          <div className="relative">
            <UserRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input id="username" autoComplete="username" className="form-input pl-9" {...register("username", { required: "Username is required" })} />
          </div>
          {errors.username ? <p className="text-sm text-red-600">{errors.username.message}</p> : null}
        </div>
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
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              className="form-input pl-9"
              {...register("password", { required: "Password is required", minLength: { value: 6, message: "Use at least 6 characters" } })}
            />
          </div>
          {errors.password ? <p className="text-sm text-red-600">{errors.password.message}</p> : null}
        </div>
        <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
          <UserPlus className="h-4 w-4" aria-hidden="true" />
          {isSubmitting ? "Creating account..." : "Register"}
        </button>
      </form>
      <p className="border-t border-slate-100 px-6 py-4 text-center text-sm text-slate-500">
        Already registered? <Link to="/login" className="font-semibold text-brand-700 hover:underline">Login</Link>
      </p>
    </div>
  );
}
