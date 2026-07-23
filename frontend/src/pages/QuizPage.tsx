import { useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, CircleCheck, CircleX, Loader2, RotateCcw, Send, Trophy } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { getApiErrorMessage } from "../api/client";
import { startQuiz, submitQuiz } from "../services/quizService";
import type { QuizDifficulty, QuizQuestion, QuizStartResponse, QuizSubmitResponse } from "../types";

const difficulties: QuizDifficulty[] = ["easy", "medium", "hard"];

export function QuizPage() {
  const [difficulty, setDifficulty] = useState<QuizDifficulty>("easy");
  const [questionCount, setQuestionCount] = useState(5);
  const [quiz, setQuiz] = useState<QuizStartResponse | null>(null);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [result, setResult] = useState<QuizSubmitResponse | null>(null);

  const startMutation = useMutation({
    mutationFn: startQuiz,
    onSuccess: (data) => {
      setQuiz(data);
      setAnswers({});
      setCurrentIndex(0);
      setResult(null);
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const submitMutation = useMutation({
    mutationFn: submitQuiz,
    onSuccess: setResult,
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const currentQuestion = quiz?.questions[currentIndex];
  const selectedAnswer = currentQuestion ? answers[currentQuestion.id] : undefined;
  const progress = quiz ? ((currentIndex + 1) / quiz.questions.length) * 100 : 0;

  const reviewByQuestion = useMemo(() => {
    const map = new Map<number, QuizSubmitResponse["results"][number]>();
    result?.results.forEach((item) => map.set(item.question_id, item));
    return map;
  }, [result]);

  const handleStart = () => {
    startMutation.mutate({
      difficulty,
      question_count: questionCount,
    });
  };

  const handleSubmit = () => {
    if (!quiz) return;
    submitMutation.mutate({
      quiz_id: quiz.quiz_id,
      answers: quiz.questions.map((question) => ({
        question_id: question.id,
        selected: answers[question.id],
      })),
    });
  };

  const restart = () => {
    setQuiz(null);
    setResult(null);
    setAnswers({});
    setCurrentIndex(0);
  };

  if (result && quiz) {
    const correct = result.score;
    const wrong = Math.max(result.total - result.score, 0);
    return (
      <main className="min-h-0 flex-1 overflow-y-auto bg-slate-50 px-4 py-5 sm:px-6">
        <div className="mx-auto max-w-6xl space-y-5">
          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-brand-700">Final Score</p>
                <h1 className="mt-1 text-3xl font-bold text-slate-950">{result.score} / {result.total}</h1>
                <p className="mt-1 text-sm text-slate-500">{result.percentage}% completed correctly</p>
              </div>
              <button type="button" onClick={restart} className="btn-secondary">
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                New Quiz
              </button>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <Metric label="Percentage" value={`${result.percentage}%`} />
              <Metric label="Correct Answers" value={String(correct)} />
              <Metric label="Wrong Answers" value={String(wrong)} />
            </div>
          </section>

          <section className="space-y-3">
            <div className="flex items-end justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-slate-950">Review</h2>
                <p className="mt-1 text-sm text-slate-500">Check each answer and the correct meaning.</p>
              </div>
            </div>
            <div className="grid gap-3">
              {quiz.questions.map((question) => (
                <ReviewCard key={question.id} question={question} result={reviewByQuestion.get(question.id)} />
              ))}
            </div>
          </section>

        </div>
      </main>
    );
  }

  if (quiz && currentQuestion) {
    const isLast = currentIndex === quiz.questions.length - 1;
    const allAnswered = quiz.questions.every((question) => answers[question.id] !== undefined);
    return (
      <main className="min-h-0 flex-1 overflow-y-auto bg-slate-50 px-4 py-5 sm:px-6">
        <div className="mx-auto max-w-4xl">
          <div className="mb-5">
            <div className="flex items-center justify-between text-sm font-semibold text-slate-600">
              <span>Question {currentIndex + 1} of {quiz.questions.length}</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
              <div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <p className="text-sm font-semibold capitalize text-brand-700">{currentQuestion.type.replace(/_/g, " ")}</p>
            <h1 className="mt-3 text-2xl font-bold leading-relaxed text-slate-950">{currentQuestion.proverb}</h1>
            <p className="mt-3 text-base font-semibold text-slate-700">{currentQuestion.question}</p>

            <div className="mt-5 grid gap-3">
              {currentQuestion.options.map((option, index) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setAnswers((prev) => ({ ...prev, [currentQuestion.id]: index }))}
                  className={`flex min-h-14 items-start gap-3 rounded-lg border p-4 text-left text-sm font-semibold transition ${
                    selectedAnswer === index
                      ? "border-brand-600 bg-brand-50 text-brand-900 ring-4 ring-brand-100"
                      : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-current text-xs">{index + 1}</span>
                  <span className="leading-6">{option}</span>
                </button>
              ))}
            </div>

            <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
              <button type="button" className="btn-secondary" disabled={currentIndex === 0} onClick={() => setCurrentIndex((value) => value - 1)}>
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                Previous
              </button>
              <div className="flex gap-3">
                {!isLast ? (
                  <button type="button" className="btn-primary" disabled={selectedAnswer === undefined} onClick={() => setCurrentIndex((value) => value + 1)}>
                    Next
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </button>
                ) : (
                  <button type="button" className="btn-primary" disabled={!allAnswered || submitMutation.isPending} onClick={handleSubmit}>
                    {submitMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Send className="h-4 w-4" aria-hidden="true" />}
                    Submit
                  </button>
                )}
              </div>
            </div>
          </section>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-0 flex-1 overflow-y-auto bg-slate-50 px-4 py-5 sm:px-6">
      <div className="mx-auto max-w-4xl">
        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-brand-100 p-3 text-brand-700">
              <Trophy className="h-6 w-6" aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-950">
  Burmese Proverbs Hub Quiz
</h1>
<p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
  Challenge yourself with AI-generated quizzes based on authentic Myanmar proverbs. Learn, practice, and preserve the wisdom of Myanmar's traditional sayings.
</p>
            </div>
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <label className="space-y-2">
              <span className="form-label">Difficulty</span>
              <select className="form-input capitalize" value={difficulty} onChange={(event) => setDifficulty(event.target.value as QuizDifficulty)}>
                {difficulties.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
            <label className="space-y-2">
              <span className="form-label">Number of questions</span>
              <input className="form-input" type="number" min={1} max={20} value={questionCount} onChange={(event) => setQuestionCount(Number(event.target.value))} />
            </label>
          </div>

          <button type="button" className="btn-primary mt-6 w-full sm:w-auto" disabled={startMutation.isPending} onClick={handleStart}>
            {startMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <CheckCircle2 className="h-4 w-4" aria-hidden="true" />}
            Start Quiz
          </button>
        </section>
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p className="text-sm font-semibold text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-950">{value}</p>
    </div>
  );
}

function ReviewCard({ question, result }: { question: QuizQuestion; result?: QuizSubmitResponse["results"][number] }) {
  const selected = result?.selected ?? undefined;
  const isCorrect = Boolean(result?.correct);
  const selectedAnswer = selected === undefined ? "No answer" : question.options[selected];
  const correctAnswer = result ? question.options[result.correct_answer] : "";

  return (
    <article className={`overflow-hidden rounded-lg border bg-white shadow-sm ${isCorrect ? "border-emerald-200" : "border-red-200"}`}>
      <div className="flex flex-col gap-3 border-b border-slate-100 px-4 py-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-bold text-slate-600">Q{question.id}</span>
            <p className="text-sm font-bold text-slate-950">{question.question}</p>
          </div>
          <p className="mt-2 break-words text-base font-semibold leading-7 text-slate-800">{question.proverb}</p>
        </div>
        <span
          className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold ${
            isCorrect ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
          }`}
        >
          {isCorrect ? <CircleCheck className="h-3.5 w-3.5" aria-hidden="true" /> : <CircleX className="h-3.5 w-3.5" aria-hidden="true" />}
          {isCorrect ? "Correct" : "Wrong"}
        </span>
      </div>

      <div className="grid gap-3 p-4 md:grid-cols-2">
        <AnswerBlock label="Your Answer" value={selectedAnswer} tone={isCorrect ? "correct" : "wrong"} />
        <AnswerBlock label="Correct Answer" value={correctAnswer} tone="correct" />
      </div>

    </article>
  );
}

function AnswerBlock({ label, value, tone }: { label: string; value: string; tone: "correct" | "wrong" }) {
  const toneClass =
    tone === "correct"
      ? "border-emerald-200 bg-emerald-50/70 text-emerald-950"
      : "border-red-200 bg-red-50/70 text-red-950";

  return (
    <div className={`rounded-lg border p-3 ${toneClass}`}>
      <p className="text-xs font-bold uppercase opacity-70">{label}</p>
      <p className="mt-1 text-sm font-semibold leading-6">{value}</p>
    </div>
  );
}
