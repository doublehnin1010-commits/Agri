import { Outlet } from "react-router-dom";

export function AuthLayout() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-cream px-4 py-10 sm:px-6 lg:px-10">
      <div className="w-full max-w-5xl">
        <Outlet />
      </div>
    </main>
  );
}
