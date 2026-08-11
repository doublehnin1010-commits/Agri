import { Outlet } from "react-router-dom";
import { Brand } from "../components/Brand";

export function AuthLayout() {
  return (
    <main className="min-h-screen overflow-x-hidden bg-cream">
      <div className="grid min-h-screen md:grid-cols-2">
        <section className="hidden min-h-screen bg-[#0F172A] text-white md:block">
          <div className="sticky top-0 flex h-screen flex-col justify-between px-8 py-8 lg:px-10 xl:px-14">
            <div className="[&_.text-slate-500]:text-slate-400 [&_.text-slate-950]:text-white">
              <Brand />
            </div>

            <div className="max-w-xl">
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-300">
                Preserve Heritage | Empower Learning
              </p>
              <h1 className="mt-5 text-3xl font-bold leading-tight text-white lg:text-4xl xl:text-5xl">
                Discover the Timeless Wisdom of Myanmar Proverbs
              </h1>
              <p className="mt-5 text-sm leading-7 text-slate-300 lg:text-base">
                Experience an AI-powered educational platform that brings Myanmar proverbs to life through interactive
                conversations, voice-enabled learning, cultural insights, and practical real-world examples.
              </p>
            </div>

            <p className="max-w-lg text-sm leading-6 text-slate-400">
              Built for Burmese Proverbs Hub learners, teachers, and admins.
            </p>
          </div>
        </section>

        <section className="flex min-h-screen items-center justify-center px-4 py-8 sm:px-8 md:h-screen md:overflow-y-auto">
          <div className="w-full max-w-md">
            <div className="mb-7 md:hidden">
              <Brand />
            </div>
            <Outlet />
          </div>
        </section>
      </div>
    </main>
  );
}
