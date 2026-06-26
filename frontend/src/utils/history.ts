import type { GroupedHistory, HistoryConversation, HistoryGroupKey } from "../types/history";

const GROUP_LABELS: Record<HistoryGroupKey, string> = {
  today: "Today",
  yesterday: "Yesterday",
  previous7Days: "Previous 7 Days",
  older: "Older",
};

export function getConversationTitle(conversation: Pick<HistoryConversation, "title" | "messages">): string {
  const existingTitle = conversation.title?.trim();
  const firstUserMessage = conversation.messages.find((message) => message.role === "user")?.content.trim();
  return truncateTitle(existingTitle || firstUserMessage || "Untitled conversation");
}

export function truncateTitle(title: string, limit = 40): string {
  const normalized = title.replace(/\s+/g, " ").trim();
  return normalized.length > limit ? `${normalized.slice(0, limit - 1)}...` : normalized;
}

export function groupConversationsByDate(conversations: HistoryConversation[]): GroupedHistory[] {
  const grouped: Record<HistoryGroupKey, HistoryConversation[]> = {
    today: [],
    yesterday: [],
    previous7Days: [],
    older: [],
  };

  conversations
    .slice()
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .forEach((conversation) => {
      grouped[getDateGroup(conversation.created_at)].push({
        ...conversation,
        title: getConversationTitle(conversation),
      });
    });

  return (Object.keys(grouped) as HistoryGroupKey[])
    .map((key) => ({ key, label: GROUP_LABELS[key], conversations: grouped[key] }))
    .filter((group) => group.conversations.length > 0);
}

function getDateGroup(value: string): HistoryGroupKey {
  const date = startOfDay(new Date(value));
  const today = startOfDay(new Date());
  const diffDays = Math.floor((today.getTime() - date.getTime()) / 86_400_000);

  if (diffDays <= 0) return "today";
  if (diffDays === 1) return "yesterday";
  if (diffDays <= 7) return "previous7Days";
  return "older";
}

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}
