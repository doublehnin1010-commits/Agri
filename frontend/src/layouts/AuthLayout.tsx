import { Outlet } from "react-router-dom";
import { Brand } from "../components/Brand";

export function AuthLayout() {
  return (
    <main className="min-h-screen bg-slate-50">
      <div className="grid min-h-screen lg:grid-cols-[0.9fr_1.1fr]">
        <section className="hidden bg-slate-950 p-10 text-white lg:flex lg:flex-col lg:justify-between">
          <Brand />
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-brand-100">
              Educational AI Platform
            </p>
            <h1 className="mt-5 max-w-xl text-5xl font-bold leading-tight">
              Myanmar Proverbs AI Tutor
            </h1>
            <p className="mt-5 max-w-lg text-base leading-7 text-slate-300">
              Learn proverb meanings, examples, and cultural context through a focused AI tutor experience.
            </p>
          </div>
          <p className="text-sm text-slate-400">Built for Myanmar Unicode and modern classroom workflows.</p>
        </section>
        <section className="flex min-h-screen items-center justify-center p-4 sm:p-8">
          <div className="w-full max-w-md">
            <div className="mb-8 lg:hidden">
              <Brand />
            </div>
            <Outlet />
          </div>
        </section>
      </div>
    </main>
  );
}
