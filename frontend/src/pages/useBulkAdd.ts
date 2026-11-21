/**
 * The cart bar's "Add all N" (mame-curator-1234, CR-09-12: out of
 * `useLibraryController.ts`, over its size cap).
 */
import { useState } from "react";
import { toast } from "sonner";
import { apiRequest } from "@/api/client";
import { GamesPageSchema, type GamesPage } from "@/api/types";
import { MAX_CART_SIZE, type UseCartResult } from "@/hooks/useCart";
import { toQueryString, type GamesQuery } from "@/hooks/useGames";
import { toastApiError } from "@/lib/apiErrorToast";
import { strings } from "@/strings";

export function useBulkAdd(
  cart: UseCartResult,
  query: Omit<GamesQuery, "page">,
  total: number,
) {
  // FP24-M + S: handleBulkAdd promises "Add all N" where N is the
  // filter-result total — but the loaded `cards` may be only the pages
  // scrolled to so far. Iterate the same filter at the backend's
  // page_size=500 cap until we've covered `total`, then `addAll`.
  // Surfaces MAX_CART_SIZE truncation as a toast so the user knows
  // some items didn't fit.
  // mame-curator-1234 (CR-09-7): a press while it runs is ignored.
  const [bulkAdding, setBulkAdding] = useState(false);
  const handleBulkAdd = async () => {
    const PAGE_SIZE = 500;
    const collected: string[] = [];
    const targetTotal = Math.min(total, MAX_CART_SIZE);
    let page = 1;
    setBulkAdding(true);
    try {
      while (collected.length < targetTotal) {
        const pageQuery: GamesQuery = { ...query, page, pageSize: PAGE_SIZE };
        const pageData = await apiRequest<GamesPage>(
          `/api/games?${toQueryString(pageQuery)}`,
          GamesPageSchema,
        );
        collected.push(...pageData.items.map((c) => c.short_name));
        if (pageData.items.length === 0) break;
        page += 1;
      }
    } catch (err) {
      toastApiError(err);
      return;
    } finally {
      setBulkAdding(false);
    }
    const { truncated } = cart.addAll(collected);
    if (truncated > 0) {
      toast.warning(strings.library.cart.maxCartReachedToast(MAX_CART_SIZE));
    }
  };

  return { handleBulkAdd, bulkAdding };
}
