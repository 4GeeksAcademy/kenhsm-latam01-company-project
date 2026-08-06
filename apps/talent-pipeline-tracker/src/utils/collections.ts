export type SortDirection = "asc" | "desc";

export function filterCollection<T>(
  collection: readonly T[],
  predicate: (item: T) => boolean,
): T[] {
  if (collection.length === 0) {
    return [];
  }

  return collection.filter(predicate);
}

export function sortCollection<T, V extends string | number | Date>(
  collection: readonly T[],
  selector: (item: T) => V,
  direction: SortDirection = "asc",
): T[] {
  if (collection.length <= 1) {
    return [...collection];
  }

  const multiplier = direction === "asc" ? 1 : -1;
  return [...collection].sort((left, right) => {
    const leftValue = selector(left);
    const rightValue = selector(right);

    const normalizedLeft = leftValue instanceof Date ? leftValue.getTime() : leftValue;
    const normalizedRight = rightValue instanceof Date ? rightValue.getTime() : rightValue;

    if (normalizedLeft < normalizedRight) {
      return -1 * multiplier;
    }

    if (normalizedLeft > normalizedRight) {
      return 1 * multiplier;
    }

    return 0;
  });
}

export function groupCollectionBy<T, K extends PropertyKey>(
  collection: readonly T[],
  keySelector: (item: T) => K,
): Record<K, T[]> {
  return collection.reduce<Record<K, T[]>>((accumulator, item) => {
    const key = keySelector(item);

    if (!accumulator[key]) {
      accumulator[key] = [];
    }

    accumulator[key].push(item);
    return accumulator;
  }, {} as Record<K, T[]>);
}
