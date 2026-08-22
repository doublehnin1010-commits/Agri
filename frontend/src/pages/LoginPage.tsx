import { Bug, Droplets, Leaf, LockKeyhole, LogIn, Mail, Sprout, Wheat } from "lucide-react";
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

const capabilities = [
  { icon: Wheat, text: "စိုက်ပျိုးရေးအကြံပြုချက်များ" },
  { icon: Sprout, text: "မြန်မာလို မေးနိုင်ပါတယ်" },
  { icon: Droplets, text: "ရေသွင်းစနစ် အကြံပြုချက်များ" },
  { icon: Bug, text: "ပိုးမွှားနှင့် ရောဂါရှာဖွေခြင်း" },
  { icon: Leaf, text: "မြေဆီလွှာတိုးတက်စေရန် နည်းလမ်းများ" },
  { icon: Wheat, text: "စိုက်ပျိုးရေးစာရွက်စာတမ်းများ" },
];

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
      toast.success("အောင်မြင်စွာ ဝင်ရောက်ပြီးပါပြီ။");
      const requestedPath = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
      const redirectTo = user.role === "admin" ? "/admin" : requestedPath ?? "/dashboard";
      navigate(redirectTo, { replace: true });
    } catch (error) {
      toast.error(getApiErrorMessage(error));
    }
  };

  return (
    <div className="grid overflow-hidden rounded-lg border border-cream-200 bg-white shadow-soft lg:grid-cols-[1.05fr_0.95fr]">
      <section className="bg-brand-50 px-6 py-7 sm:px-8">
        <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-lg bg-brand-700 shadow-sm">
          <img src="/doh-oo-gyi.png" alt="တို့ဦးကြီး logo" className="h-full w-full object-cover" />
        </div>
        <h1 className="mt-5 text-3xl font-bold leading-tight text-brand-700">တို့ဦးကြီး</h1>
        <h2 className="mt-2 text-lg font-semibold text-[#263238]">စိုက်ပျိုးရေးအကြံပေး AI</h2>
        <p className="mt-4 text-sm leading-7 text-[#607D8B]">
          သီးနှံစိုက်ပျိုးခြင်း၊ အပင်ရောဂါနှင့် မြေဩဇာဆိုင်ရာ အကြံပြုချက်များကို လွယ်ကူမြန်ဆန်စွာ ရယူနိုင်ပါသည်။
        </p>
      

        <div className="mt-6 border-t border-brand-100 pt-5">
          <p className="text-sm font-bold text-brand-700">လုပ်ဆောင်ချက်များ</p>
          <div className="mt-3 grid gap-2">
            {capabilities.map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-center gap-3 rounded-lg border border-brand-100 bg-white px-3 py-2 text-sm font-semibold text-[#263238]">
                <Icon className="h-4 w-4 text-brand-600" aria-hidden="true" />
                <span>{text}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-7 sm:px-8">
        <div>
          <p className="text-sm font-bold text-brand-700">ပြန်လည်ကြိုဆိုပါတယ်</p>
          <h2 className="mt-2 text-2xl font-bold text-[#263238]">အကောင့်ဝင်ရန်</h2>
        </div>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div className="space-y-2">
            <label className="form-label" htmlFor="email">အီးမေးလ်</label>
            <div className="relative">
              <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#607D8B]" aria-hidden="true" />
              <input id="email" type="email" autoComplete="email" placeholder="အီးမေးလ်လိပ်စာ ထည့်ပါ" className="form-input pl-9" {...register("email", { required: "အီးမေးလ် လိုအပ်ပါသည်" })} />
            </div>
            {errors.email ? <p className="text-sm text-brand-700">{errors.email.message}</p> : null}
          </div>

          <div className="space-y-2">
            <label className="form-label" htmlFor="password">စကားဝှက်</label>
            <div className="relative">
              <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#607D8B]" aria-hidden="true" />
              <input id="password" type="password" autoComplete="current-password" placeholder="စကားဝှက် ထည့်ပါ" className="form-input pl-9" {...register("password", { required: "စကားဝှက် လိုအပ်ပါသည်" })} />
            </div>
            {errors.password ? <p className="text-sm text-brand-700">{errors.password.message}</p> : null}
          </div>

          

          <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
            <LogIn className="h-4 w-4" aria-hidden="true" />
            {isSubmitting ? "ဝင်ရောက်နေပါသည်..." : "အကောင့်ဝင်မည်"}
          </button>
        </form>

        <p className="mt-6 border-t border-cream-200 pt-4 text-center text-sm text-[#607D8B]">
          အကောင့်မရှိသေးပါသလား။ <Link to="/register" className="font-semibold text-brand-700 hover:underline">အကောင့်ဖွင့်ရန်</Link>
        </p>
      </section>
    </div>
  );
}

