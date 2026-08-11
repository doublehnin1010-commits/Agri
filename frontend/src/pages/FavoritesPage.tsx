import { Heart, Loader2, Search, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import { getApiErrorMessage } from "../api/client";
import { Modal } from "../components/Modal";
import { useHistory } from "../hooks/useHistory";
import { listFavorites, removeFavorite } from "../services/favoriteService";
import type { FavoriteProverb } from "../types";

export function FavoritesPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { startNewConversation } = useHistory();
  const [selectedFavorite, setSelectedFavorite] = useState<FavoriteProverb | null>(null);
  const { data = [], isLoading, error } = useQuery({
    queryKey: ["favorites"],
    queryFn: listFavorites,
  });

  const removeMutation = useMutation({
    mutationFn: removeFavorite,
    onSuccess: async () => {
      toast.success("Removed from favorites");
      await queryClient.invalidateQueries({ queryKey: ["favorites"] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  return (
    <main className="min-h-0 flex-1 overflow-y-auto bg-slate-50 px-4 py-5 sm:px-6">
      <div className="mx-auto max-w-6xl space-y-5">
        <header className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-start gap-3">
            <span className="rounded-lg bg-red-50 p-3 text-red-600">
              <Heart className="h-6 w-6 fill-current" aria-hidden="true" />
            </span>
            <div>
              <h1 className="text-2xl font-bold text-slate-950">My Favorite Proverbs</h1>
              <p className="mt-1 text-sm leading-6 text-slate-500">Saved proverbs you want to revisit later.</p>
            </div>
          </div>
        </header>

        {isLoading ? <FavoritesSkeleton /> : null}

        {!isLoading && error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">
            {getApiErrorMessage(error)}
          </div>
        ) : null}

        {!isLoading && !error && !data.length ? (
          <EmptyFavorites
            onExplore={() => {
              startNewConversation();
              navigate("/dashboard");
            }}
          />
        ) : null}

        {!isLoading && !error && data.length ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.map((favorite) => (
              <FavoriteCard
                key={favorite.id}
                favorite={favorite}
                removing={removeMutation.isPending}
                onView={() => setSelectedFavorite(favorite)}
                onRemove={() => removeMutation.mutate(favorite.id)}
              />
            ))}
          </div>
        ) : null}
      </div>

      <FavoriteDetailsModal favorite={selectedFavorite} onClose={() => setSelectedFavorite(null)} />
    </main>
  );
}

function FavoriteCard({
  favorite,
  removing,
  onView,
  onRemove,
}: {
  favorite: FavoriteProverb;
  removing: boolean;
  onView: () => void;
  onRemove: () => void;
}) {
  return (
    <article className="flex min-h-64 flex-col rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="min-w-0 flex-1">
        <div className="mb-3 flex items-center justify-between gap-3">
          <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-bold text-brand-700">
            {favorite.category || favorite.keyword || "Proverb"}
          </span>
          <Heart className="h-4 w-4 fill-red-500 text-red-500" aria-hidden="true" />
        </div>
        <h2 className="break-words text-lg font-bold leading-8 text-slate-950">{favorite.proverb}</h2>
        <p className="mt-3 line-clamp-4 text-sm leading-6 text-slate-600">{favorite.meaning || favorite.english_meaning || "No meaning available."}</p>
      </div>
      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        <button type="button" onClick={onView} className="btn-secondary flex-1">
          <Search className="h-4 w-4" aria-hidden="true" />
          View Details
        </button>
        <button type="button" onClick={onRemove} disabled={removing} className="btn-secondary flex-1 text-red-600 hover:text-red-700">
          {removing ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Trash2 className="h-4 w-4" aria-hidden="true" />}
          Remove
        </button>
      </div>
    </article>
  );
}

function FavoriteDetailsModal({ favorite, onClose }: { favorite: FavoriteProverb | null; onClose: () => void }) {
  return (
    <Modal title="Proverb Details" isOpen={Boolean(favorite)} onClose={onClose}>
      {favorite ? (
        <div className="space-y-4">
          <div>
            <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-bold text-brand-700">
              {favorite.category || favorite.keyword || "Proverb"}
            </span>
            <h3 className="mt-3 break-words text-xl font-bold leading-9 text-slate-950">{favorite.proverb}</h3>
          </div>

          <DetailBlock label="Meaning" value={favorite.meaning || favorite.english_meaning || "No meaning available."} />
          {favorite.english_meaning && favorite.english_meaning !== favorite.meaning ? (
            <DetailBlock label="English Meaning" value={favorite.english_meaning} />
          ) : null}
          {favorite.example ? <DetailBlock label="Example" value={favorite.example} /> : null}
        </div>
      ) : null}
    </Modal>
  );
}

function DetailBlock({ label, value }: { label: string; value: string }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs font-bold uppercase text-slate-500">{label}</p>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-800">{value}</p>
    </section>
  );
}

function EmptyFavorites({ onExplore }: { onExplore: () => void }) {
  return (
    <section className="flex min-h-80 flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center">
      <div className="rounded-lg bg-slate-100 p-4 text-slate-500">
        <Heart className="h-7 w-7" aria-hidden="true" />
      </div>
      <h2 className="mt-4 text-lg font-bold text-slate-950">No favorite proverbs yet.</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">Save useful proverbs from chat answers and they will appear here.</p>
      <button type="button" onClick={onExplore} className="btn-primary mt-5">
        Explore Proverbs
      </button>
    </section>
  );
}

function FavoritesSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {[0, 1, 2, 3, 4, 5].map((item) => (
        <div key={item} className="h-64 animate-pulse rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="h-5 w-24 rounded bg-slate-100" />
          <div className="mt-5 h-6 w-4/5 rounded bg-slate-100" />
          <div className="mt-4 space-y-2">
            <div className="h-3 rounded bg-slate-100" />
            <div className="h-3 rounded bg-slate-100" />
            <div className="h-3 w-2/3 rounded bg-slate-100" />
          </div>
        </div>
      ))}
    </div>
  );
}
