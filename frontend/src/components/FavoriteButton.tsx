import { Heart, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { getApiErrorMessage } from "../api/client";
import { addFavorite, checkFavorite, removeFavorite } from "../services/favoriteService";

interface FavoriteButtonProps {
  proverbId: string;
  initialFavorite?: boolean;
  compact?: boolean;
  onChange?: (favorite: boolean) => void;
}

export function FavoriteButton({ proverbId, initialFavorite = false, compact = false, onChange }: FavoriteButtonProps) {
  const [favorite, setFavorite] = useState(initialFavorite);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    setFavorite(initialFavorite);
    void checkFavorite(proverbId)
      .then((result) => {
        if (mounted) setFavorite(result.favorite);
      })
      .catch(() => undefined);
    return () => {
      mounted = false;
    };
  }, [initialFavorite, proverbId]);

  const toggleFavorite = async () => {
    setLoading(true);
    try {
      const result = favorite ? await removeFavorite(proverbId) : await addFavorite(proverbId);
      setFavorite(result.favorite);
      onChange?.(result.favorite);
      if (result.message) toast.success(result.message);
    } catch (error) {
      toast.error(getApiErrorMessage(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      onClick={toggleFavorite}
      disabled={loading}
      className={`inline-flex items-center justify-center gap-2 rounded-lg border font-semibold transition focus:outline-none focus:ring-4 focus:ring-red-100 disabled:cursor-not-allowed disabled:opacity-60 ${
        compact ? "h-9 px-3 text-xs" : "px-4 py-2.5 text-sm"
      } ${
        favorite
          ? "border-red-200 bg-red-50 text-red-600 hover:bg-red-100"
          : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:text-red-600"
      }`}
      aria-pressed={favorite}
      aria-label={favorite ? "Remove from favorites" : "Add to favorites"}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
      ) : (
        <Heart className={`h-4 w-4 ${favorite ? "fill-current" : ""}`} aria-hidden="true" />
      )}
      {favorite ? "Favorite" : "Favorite"}
    </button>
  );
}
