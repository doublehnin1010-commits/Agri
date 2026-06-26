import { UserPlus } from "lucide-react";
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
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
      <h1 className="text-2xl font-bold text-slate-950">Create account</h1>
      <p className="mt-2 text-sm leading-6 text-slate-500">Start learning Myanmar proverbs with guided AI support.</p>
      <form className="mt-6 space-y-4" onSubmit={handleSubmit(onSubmit)}>
        <div className="space-y-2">
          <label className="form-label" htmlFor="username">Username</label>
          <input id="username" className="form-input" {...register("username", { required: "Username is required" })} />
          {errors.username ? <p className="text-sm text-red-600">{errors.username.message}</p> : null}
        </div>
        <div className="space-y-2">
          <label className="form-label" htmlFor="email">Email</label>
          <input id="email" type="email" className="form-input" {...register("email", { required: "Email is required" })} />
          {errors.email ? <p className="text-sm text-red-600">{errors.email.message}</p> : null}
        </div>
        <div className="space-y-2">
          <label className="form-label" htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            className="form-input"
            {...register("password", { required: "Password is required", minLength: { value: 6, message: "Use at least 6 characters" } })}
          />
          {errors.password ? <p className="text-sm text-red-600">{errors.password.message}</p> : null}
        </div>
        <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
          <UserPlus className="h-4 w-4" aria-hidden="true" />
          {isSubmitting ? "Creating account..." : "Register"}
        </button>
      </form>
      <p className="mt-5 text-center text-sm text-slate-500">
        Already registered? <Link to="/login" className="font-semibold text-brand-700 hover:underline">Login</Link>
      </p>
    </div>
  );
}
