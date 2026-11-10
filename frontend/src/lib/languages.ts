/** mame-curator-1217: the same languages kept, whatever their order. */
export function sameLanguages(a: string[], b: string[]): boolean {
  const set = new Set(b);
  return a.length === set.size && a.every((name) => set.has(name));
}
