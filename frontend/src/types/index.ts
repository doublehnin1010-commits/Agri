export type UserRole = "user" | "admin";

export interface User {
  id?: string;
  name?: string;
  username?: string;
  email: string;
  role: UserRole;
}

export interface AuthResponse {
  access_token?: string;
  token?: string;
  token_type?: string;
  role?: UserRole;
  user?: User;
}

export interface RegisterPayload {
  username: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface SourceItem {
  id?: string | null;
  keyword?: string | null;
  category?: string | null;
  proverb?: string | null;
  meaning?: string | null;
  english_meaning?: string | null;
  example?: string | null;
  score?: number | null;
}

export interface AiAnswer {
  proverb_id?: string | null;
  proverb?: string | null;
  meaning_simple_mm?: string | null;
  meaning?: string | null;
  example_mm?: string | null;
  example?: string | null;
  language?: "my" | "en" | string | null;
  image_url?: string | null;
  image_prompt?: string | null;
  sources?: SourceItem[];
  [key: string]: unknown;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  answer?: AiAnswer;
  createdAt: string;
}

export interface HistoryApiItem {
  user_message: string;
  assistant_message: AiAnswer;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  messages: ChatMessage[];
}

export interface Proverb {
  id: string;
  keyword?: string | null;
  category?: string | null;
  proverb: string;
  meaning?: string | null;
  english_meaning?: string | null;
  example?: string | null;
}

export interface FavoriteStatus {
  message?: string | null;
  favorite: boolean;
}

export interface FavoriteProverb extends Proverb {
  created_at: string;
}

export type QuizDifficulty = "easy" | "medium" | "hard";

export type QuizQuestionType =
  | "multiple_choice"
  | "meaning_identification"
  | "situation_matching"
  | "fill_in_the_blank";

export interface QuizStartPayload {
  category?: string;
  difficulty?: QuizDifficulty;
  question_count: number;
}

export interface QuizQuestion {
  id: number;
  type: QuizQuestionType;
  proverb: string;
  question: string;
  options: string[];
}

export interface QuizStartResponse {
  quiz_id: string;
  questions: QuizQuestion[];
}

export interface QuizSubmitPayload {
  quiz_id: string;
  answers: Array<{
    question_id: number;
    selected: number;
  }>;
}

export interface QuizResultItem {
  question_id: number;
  correct: boolean;
  correct_answer: number;
  selected?: number | null;
  explanation: string;
}

export interface QuizSubmitResponse {
  score: number;
  total: number;
  percentage: number;
  results: QuizResultItem[];
  recommended_proverbs: Proverb[];
}

export interface ImportResult {
  success: boolean;
  documents_imported: number;
  embeddings_created: number;
  failed: number;
  processing_time_seconds: number;
}

export interface ImportJobUploadResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface ImportJobProgress {
  success?: boolean;
  job_id: string;
  status: "uploaded" | "processing" | "embedding" | "completed" | "failed";
  current?: number;
  total?: number;
  progress?: number;
  step?: string;
  failed?: number;
  estimated_remaining?: number;
  documents_imported?: number;
  embeddings_created?: number;
  documents?: number;
  processing_time_seconds?: number;
  error?: string;
}
