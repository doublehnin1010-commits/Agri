import { Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useEffect, useRef } from "react";
import { ChatBubble } from "./ChatBubble";
import type { HistoryMessage } from "../types/history";
import type { ChatMessage } from "../types";
import { makeId } from "../utils/answer";

interface ChatMessagesProps {
  messages: HistoryMessage[];
  isResponding?: boolean;
  emptyStateTitle?: string;
  emptyStateDescription?: string;
}

export function ChatMessages({
  messages,
  isResponding = false,
  emptyStateTitle = "တို့ဦးကြီးကို မေးမြန်းပါ",
  emptyStateDescription = `စိုက်ပျိုးရေးနဲ့ပတ်သက်တာတွေကို လွတ်လပ်စွာ မေးမြန်းနိုင်ပါတယ်။ 🌱

🌾 သီးနှံစိုက်ပျိုးနည်း
🐛 အပင်ရောဂါနဲ့ ပိုးမွှားများ
🌱 မြေဆီလွှာနဲ့ မြေဩဇာ
💧 ရေသွင်းခြင်းနဲ့ ရေစီမံခန့်ခွဲမှု
📷 အပင်ရဲ့ပုံတင်ပြီး ဖြစ်နိုင်တဲ့ရောဂါတွေကို မေးမြန်းနိုင်ပါတယ်။
🎤 အသံနဲ့လည်း မေးမြန်းနိုင်ပါတယ်။

မြန်မာလိုဖြစ်စေ English လိုဖြစ်စေ မေးနိုင်ပါတယ်။ ရရှိထားတဲ့ စိုက်ပျိုးရေးအချက်အလက်များကို အခြေခံပြီး နားလည်ရလွယ်ကူအောင် ဖြေကြားပေးပါမယ်။

**ဥပမာ —**

“စပါးအရွက်တွေ ဝါလာတာ ဘာကြောင့်လဲ?”

“ဒီပုံထဲက အပင်မှာ ဘာဖြစ်နေတာလဲ?” 

“ခရမ်းချဉ်သီး စိုက်တဲ့အခါ ဘာမြေဩဇာသုံးသင့်လဲ?”`,
}: ChatMessagesProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isResponding]);

  if (!messages.length) {
    return (
      <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col justify-center ">
        <div className="rounded-lg border border-cream-200 bg-white px-5 py-8 text-center shadow-sm sm:px-8">
          <div className="mx-auto flex h-14 w-14 items-center justify-center overflow-hidden rounded-lg bg-brand-700 shadow-sm">
            <img src="/doh-oo-gyi.png" alt="တို့ဦးကြီး logo" className="h-full w-full object-cover" />
          </div>
          <h2 className="mt-4 text-xl font-bold text-[#263238] sm:text-2xl">{emptyStateTitle}</h2>
          <div className="mx-auto mt-3 max-w-2xl text-left text-sm leading-7 text-[#607D8B]">
            <ReactMarkdown
              components={{
                p: ({ children }) => <p className="mb-4 last:mb-0">{children}</p>,
                strong: ({ children }) => <strong className="font-bold text-brand-700">{children}</strong>,
              }}
            >
              {emptyStateDescription}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
      {messages.map((message) => <ChatBubble key={message.id ?? makeId("message")} message={toChatMessage(message)} />)}
      {isResponding ? <div className="flex items-center gap-3 rounded-lg border border-cream-200 bg-white px-4 py-3 text-sm font-semibold text-[#607D8B] shadow-sm"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-700"><Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /></span><span>Searching agriculture documents...</span></div> : null}
      <div ref={scrollRef} />
    </div>
  );
}

function toChatMessage(message: HistoryMessage): ChatMessage {
  return { id: message.id ?? makeId("message"), role: message.role, content: message.content, imageUrl: message.imageUrl, answer: message.answer, createdAt: message.created_at ?? new Date().toISOString() };
}


