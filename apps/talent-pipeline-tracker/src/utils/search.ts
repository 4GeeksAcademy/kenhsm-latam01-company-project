export function linearSearchIndex<T>(
  collection: readonly T[],
  predicate: (item: T) => boolean,
): number {
  if (collection.length === 0) {
    return -1;
  }

  for (let index = 0; index < collection.length; index += 1) {
    if (predicate(collection[index])) {
      return index;
    }
  }

  return -1;
}

export function binarySearchIndexBy<T, V extends string | number>(
  sortedCollection: readonly T[],
  target: V,
  selector: (item: T) => V,
): number {
  if (sortedCollection.length === 0) {
    return -1;
  }

  let left = 0;
  let right = sortedCollection.length - 1;

  while (left <= right) {
    const middle = Math.floor((left + right) / 2);
    const middleValue = selector(sortedCollection[middle]);

    if (middleValue === target) {
      return middle;
    }

    if (middleValue < target) {
      left = middle + 1;
    } else {
      right = middle - 1;
    }
  }

  return -1;
}
