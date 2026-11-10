import type { Location, MenuItem } from "../types/models.ts";

export function findLocationById(locations: Location[], id: string): Location | null {
  if (!Array.isArray(locations)) return null;

  for (const location of locations) {
    if (location != null && location.id === id) return location;
  }

  return null;
}

export function findMenuItemByName(items: MenuItem[], name: string): MenuItem | null {
  if (!Array.isArray(items) || typeof name !== "string") return null;
  const normalizedName = name.trim().toLowerCase();
  if (!normalizedName) return null;

  for (const item of items) {
    if (item != null && item.name.trim().toLowerCase() === normalizedName) return item;
  }

  return null;
}

export function binarySearchLocationByCapacity(
  sortedLocations: Location[],
  targetCapacity: number,
): number {
  if (!Array.isArray(sortedLocations) || !Number.isFinite(targetCapacity)) return -1;

  let left = 0;
  let right = sortedLocations.length - 1;

  while (left <= right) {
    const middle = left + Math.floor((right - left) / 2);
    const location = sortedLocations[middle];
    if (location == null) return -1;
    const capacity = location.seatingCapacity;

    if (capacity === targetCapacity) return middle;
    if (capacity < targetCapacity) left = middle + 1;
    else right = middle - 1;
  }

  return -1;
}