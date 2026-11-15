import { useSyncExternalStore } from "react";

/**
 * mame-curator-1143: how many fresh looks found a game a picture this
 * session. The count goes into the picture's address, so every card and
 * panel showing the game asks for the picture again instead of keeping
 * the "no picture" it already had.
 */
const looks = new Map<string, number>();
const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function notePictureLook(shortName: string): void {
  looks.set(shortName, (looks.get(shortName) ?? 0) + 1);
  for (const listener of listeners) listener();
}

export function usePictureLook(shortName: string): number {
  return useSyncExternalStore(subscribe, () => looks.get(shortName) ?? 0);
}
