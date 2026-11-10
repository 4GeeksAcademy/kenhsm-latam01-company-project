import type {
  Location,
  MenuCategory,
  MenuItem,
  Price,
  SaleTransaction,
} from "../types/models.ts";

export type SortOrder = "asc" | "desc";

export function filterSalesByLocation(
  sales: SaleTransaction[],
  locationId: string,
): SaleTransaction[] {
  if (!Array.isArray(sales)) return [];
  return sales.filter((sale) => sale != null && sale.locationId === locationId);
}

export function filterSalesByItemId(
  sales: SaleTransaction[],
  itemId: string,
): SaleTransaction[] {
  if (!Array.isArray(sales)) return [];
  return sales.filter((sale) => sale != null && sale.itemId === itemId);
}

export function filterSalesByDateRange(
  sales: SaleTransaction[],
  startDate: Date,
  endDate: Date,
): SaleTransaction[] {
  const startTime = startDate instanceof Date ? startDate.getTime() : Number.NaN;
  const endTime = endDate instanceof Date ? endDate.getTime() : Number.NaN;
  if (!Array.isArray(sales) || !Number.isFinite(startTime) || !Number.isFinite(endTime) || startTime > endTime) {
    return [];
  }

  return sales.filter((sale) => {
    const saleTime = sale?.timestamp instanceof Date ? sale.timestamp.getTime() : Number.NaN;
    return Number.isFinite(saleTime) && saleTime >= startTime && saleTime <= endTime;
  });
}

export function filterMenuItemsByCategory(
  items: MenuItem[],
  category: MenuCategory,
): MenuItem[] {
  if (!Array.isArray(items)) return [];
  return items.filter((item) => item != null && item.category === category);
}

export function filterActiveLocations(locations: Location[]): Location[] {
  if (!Array.isArray(locations)) return [];
  return locations.filter((location) => location != null && location.status === "Active");
}

export function sortLocationsByCapacity(
  locations: Location[],
  order: SortOrder,
): Location[] {
  if (!Array.isArray(locations)) return [];
  const direction = order === "asc" ? 1 : -1;
  return locations
    .filter((location) => location != null)
    .slice()
    .sort((left, right) => (left.seatingCapacity - right.seatingCapacity) * direction);
}

export function sortMenuItemsByPrice(
  items: MenuItem[],
  currency: keyof Price,
  order: SortOrder,
): MenuItem[] {
  if (!Array.isArray(items)) return [];
  const direction = order === "asc" ? 1 : -1;
  return items
    .filter((item) => item != null)
    .slice()
    .sort((left, right) => (left.basePrice[currency] - right.basePrice[currency]) * direction);
}