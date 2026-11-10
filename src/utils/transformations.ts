import type {
  Country,
  CountryMetrics,
  Location,
  MenuItem,
  PaymentMethod,
  Price,
  SaleTransaction,
  WasteReason,
  WasteRecord,
} from "../types/models.ts";

const paymentMethods: PaymentMethod[] = ["Cash", "Credit card", "Debit card", "Digital wallet"];
const wasteReasons: WasteReason[] = ["Expired", "Cooking error", "Customer return", "Damage", "Other"];
const millisecondsPerDay = 24 * 60 * 60 * 1000;

function roundToTwoDecimals(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function getUtcDateKey(date: Date): string | null {
  if (!(date instanceof Date) || !Number.isFinite(date.getTime())) return null;
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}-${String(date.getUTCDate()).padStart(2, "0")}`;
}

function getDateKeyInTimeZone(date: Date, timeZone: string): string | null {
  if (!(date instanceof Date) || !Number.isFinite(date.getTime())) return null;
  try {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).formatToParts(date);
    const values = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
    return `${values.year}-${values.month}-${values.day}`;
  } catch {
    return null;
  }
}

function getPriceAmount(price: Price, currency: keyof Price): number {
  const amount = price?.[currency];
  return Number.isFinite(amount) ? amount : 0;
}

function getLocationSales(sales: SaleTransaction[], locationId: string): SaleTransaction[] {
  if (!Array.isArray(sales)) return [];
  return sales.filter((sale) => sale != null && sale.locationId === locationId);
}

export function countBy<T, K extends PropertyKey>(
  items: T[],
  keySelector: (item: T) => K,
): Record<K, number> {
  if (!Array.isArray(items)) return {} as Record<K, number>;
  return items.reduce<Record<K, number>>((counts, item) => {
    if (item == null) return counts;
    const key = keySelector(item);
    counts[key] = (counts[key] ?? 0) + 1;
    return counts;
  }, {} as Record<K, number>);
}

export function sumBy<T>(items: T[], valueSelector: (item: T) => number): number {
  if (!Array.isArray(items)) return 0;
  return items.reduce((total, item) => {
    if (item == null) return total;
    const value = valueSelector(item);
    return Number.isFinite(value) ? total + value : total;
  }, 0);
}

export function averageBy<T>(items: T[], valueSelector: (item: T) => number): number {
  if (!Array.isArray(items)) return 0;
  const finiteValues = items
    .filter((item) => item != null)
    .map(valueSelector)
    .filter(Number.isFinite);
  if (finiteValues.length === 0) return 0;
  return roundToTwoDecimals(finiteValues.reduce((total, value) => total + value, 0) / finiteValues.length);
}

export function maxBy<T>(items: T[], valueSelector: (item: T) => number): T | null {
  if (!Array.isArray(items)) return null;
  let maximumItem: T | null = null;
  let maximumValue = Number.NEGATIVE_INFINITY;

  for (const item of items) {
    if (item == null) continue;
    const value = valueSelector(item);
    if (Number.isFinite(value) && value > maximumValue) {
      maximumItem = item;
      maximumValue = value;
    }
  }
  return maximumItem;
}

export function minBy<T>(items: T[], valueSelector: (item: T) => number): T | null {
  if (!Array.isArray(items)) return null;
  let minimumItem: T | null = null;
  let minimumValue = Number.POSITIVE_INFINITY;

  for (const item of items) {
    if (item == null) continue;
    const value = valueSelector(item);
    if (Number.isFinite(value) && value < minimumValue) {
      minimumItem = item;
      minimumValue = value;
    }
  }
  return minimumItem;
}

export function calculateDailyRevenue(
  sales: SaleTransaction[],
  date: Date,
  currency: keyof Price,
  timeZone = "UTC",
): number {
  if (!Array.isArray(sales)) return 0;
  const targetDate = getUtcDateKey(date);
  if (!targetDate) return 0;

  const dailyTotal = sales.reduce((total, sale) => {
    return sale != null && getDateKeyInTimeZone(sale.timestamp, timeZone) === targetDate
      ? total + getPriceAmount(sale.totalPrice, currency)
      : total;
  }, 0);

  return roundToTwoDecimals(dailyTotal);
}

export function calculateLocationMargin(
  sales: SaleTransaction[],
  menuItems: MenuItem[],
  locationId: string,
  currency: keyof Price,
): number {
  if (!Array.isArray(sales) || !Array.isArray(menuItems)) return 0;
  const itemsById = new Map(menuItems.filter((item) => item != null).map((item) => [item.id, item]));
  const locationSales = getLocationSales(sales, locationId);

  const totals = locationSales.reduce(
    (result, sale) => {
      const item = itemsById.get(sale.itemId);
      if (!item || !Number.isFinite(sale.quantity) || sale.quantity <= 0) return result;
      result.revenue += getPriceAmount(sale.totalPrice, currency);
      result.ingredientCost += getPriceAmount(item.ingredientCost, currency) * sale.quantity;
      return result;
    },
    { revenue: 0, ingredientCost: 0 },
  );

  if (totals.revenue <= 0) return 0;
  const margin = ((totals.revenue - totals.ingredientCost) / totals.revenue) * 100;
  return roundToTwoDecimals(Math.min(100, Math.max(0, margin)));
}

export function calculateWasteCost(
  wasteRecords: WasteRecord[],
  locationId: string,
  currency: keyof Price,
): number {
  if (!Array.isArray(wasteRecords)) return 0;
  const total = wasteRecords.reduce((sum, record) => {
    return record != null && record.locationId === locationId ? sum + getPriceAmount(record.cost, currency) : sum;
  }, 0);
  return roundToTwoDecimals(total);
}

export function convertCurrency(
  amount: number,
  fromCurrency: keyof Price,
  toCurrency: keyof Price,
): number {
  if (fromCurrency === toCurrency) return amount;
  if (!Number.isFinite(amount)) return 0;
  const convertedAmount = fromCurrency === "USD" ? amount * 4000 : amount / 4000;
  return roundToTwoDecimals(convertedAmount);
}

function estimateOperatingDays(openingYear: number, asOfDate: Date): number {
  if (!Number.isFinite(openingYear) || !(asOfDate instanceof Date) || !Number.isFinite(asOfDate.getTime())) {
    return 1;
  }
  const estimatedOpeningDate = Date.UTC(openingYear, 0, 1);
  return Math.max(1, Math.floor((asOfDate.getTime() - estimatedOpeningDate) / millisecondsPerDay));
}

export function scoreLocationPerformance(
  location: Location,
  sales: SaleTransaction[],
  wasteRecords: WasteRecord[],
  menuItems: MenuItem[],
  asOfDate: Date = new Date(),
): number {
  if (!location || !Number.isFinite(location.seatingCapacity) || location.seatingCapacity <= 0) return 0;

  const locationSales = getLocationSales(sales, location.id);
  const totalRevenueUSD = locationSales.reduce((sum, sale) => sum + getPriceAmount(sale.totalPrice, "USD"), 0);
  const operatingDays = estimateOperatingDays(location.openingYear, asOfDate);
  const averageDailyRevenueUSD = totalRevenueUSD / operatingDays;
  const revenueScore = Math.min(40, Math.max(0, (averageDailyRevenueUSD / 1000) * 40));
  const efficiencyScore = Math.min(30, (locationSales.length / location.seatingCapacity) * 30);

  const locationWasteCostUSD = calculateWasteCost(wasteRecords, location.id, "USD");
  const wasteControlScore = totalRevenueUSD > 0
    ? Math.max(0, 20 - ((locationWasteCostUSD / totalRevenueUSD) * 100 * 2))
    : 0;
  const marginScore = Math.min(
    10,
    calculateLocationMargin(sales, menuItems, location.id, "USD") / 10,
  );
  const totalScore = revenueScore + efficiencyScore + wasteControlScore + marginScore;

  return roundToTwoDecimals(Math.min(100, Math.max(0, totalScore)));
}

export function rankLocationsByPerformance(
  locations: Location[],
  sales: SaleTransaction[],
  wasteRecords: WasteRecord[],
  menuItems: MenuItem[],
  asOfDate: Date = new Date(),
): Array<{ location: Location; score: number }> {
  if (!Array.isArray(locations)) return [];

  return locations
    .filter((location) => location != null)
    .map((location, originalIndex) => ({
      location,
      score: scoreLocationPerformance(location, sales, wasteRecords, menuItems, asOfDate),
      originalIndex,
    }))
    .sort((left, right) => right.score - left.score || left.originalIndex - right.originalIndex)
    .map(({ location, score }) => ({ location, score }));
}

export function countSalesByPaymentMethod(
  sales: SaleTransaction[],
): Record<PaymentMethod, number> {
  const counts: Record<PaymentMethod, number> = {
    Cash: 0,
    "Credit card": 0,
    "Debit card": 0,
    "Digital wallet": 0,
  };
  if (!Array.isArray(sales)) return counts;

  for (const sale of sales) {
    if (sale != null && paymentMethods.includes(sale.paymentMethod)) counts[sale.paymentMethod] += 1;
  }
  return counts;
}

export function calculateAverageTicket(
  sales: SaleTransaction[],
  currency: keyof Price,
): number {
  if (!Array.isArray(sales)) return 0;
  const validSales = sales.filter((sale) => sale != null);
  if (validSales.length === 0) return 0;
  const total = validSales.reduce((sum, sale) => sum + getPriceAmount(sale.totalPrice, currency), 0);
  return roundToTwoDecimals(total / validSales.length);
}

export function findTopSellingItems(
  sales: SaleTransaction[],
  menuItems: MenuItem[],
  topN: number,
): Array<{ item: MenuItem; totalSold: number }> {
  if (!Array.isArray(sales) || !Array.isArray(menuItems) || !Number.isFinite(topN) || topN <= 0) {
    return [];
  }
  const itemsById = new Map(menuItems.filter((item) => item != null).map((item) => [item.id, item]));
  const quantityByItemId = new Map<string, number>();

  for (const sale of sales) {
    if (sale == null || !itemsById.has(sale.itemId) || !Number.isFinite(sale.quantity) || sale.quantity <= 0) continue;
    quantityByItemId.set(sale.itemId, (quantityByItemId.get(sale.itemId) ?? 0) + sale.quantity);
  }

  return Array.from(quantityByItemId, ([itemId, totalSold]) => ({
    item: itemsById.get(itemId) as MenuItem,
    totalSold,
  }))
    .sort((left, right) => right.totalSold - left.totalSold)
    .slice(0, Math.floor(topN));
}

export function groupWasteByReason(
  wasteRecords: WasteRecord[],
): Record<WasteReason, WasteRecord[]> {
  const grouped: Record<WasteReason, WasteRecord[]> = {
    Expired: [],
    "Cooking error": [],
    "Customer return": [],
    Damage: [],
    Other: [],
  };
  if (!Array.isArray(wasteRecords)) return grouped;

  for (const record of wasteRecords) {
    if (record != null && wasteReasons.includes(record.reason)) grouped[record.reason].push(record);
  }
  return grouped;
}

function createCountryMetrics(): CountryMetrics {
  return {
    totalLocations: 0,
    totalRevenue: { USD: 0, COP: 0 },
    averageRevenuePerLocation: { USD: 0, COP: 0 },
    totalSales: 0,
  };
}

export function calculateCountryComparison(
  sales: SaleTransaction[],
  locations: Location[],
  menuItems: MenuItem[],
): Record<Country, CountryMetrics> {
  const comparison: Record<Country, CountryMetrics> = {
    Colombia: createCountryMetrics(),
    USA: createCountryMetrics(),
  };
  if (!Array.isArray(sales) || !Array.isArray(locations) || !Array.isArray(menuItems)) return comparison;

  const validLocations = locations.filter((location) => location != null);
  const locationsById = new Map(validLocations.map((location) => [location.id, location]));
  const menuItemIds = new Set(menuItems.filter((item) => item != null).map((item) => item.id));

  for (const location of validLocations) {
    if (location.country === "Colombia" || location.country === "USA") {
      comparison[location.country].totalLocations += 1;
    }
  }

  for (const sale of sales) {
    if (sale == null) continue;
    const location = locationsById.get(sale.locationId);
    if (!location || !menuItemIds.has(sale.itemId)) continue;
    const country = location.country;
    const metrics = comparison[country];
    metrics.totalRevenue.USD += getPriceAmount(sale.totalPrice, "USD");
    metrics.totalRevenue.COP += getPriceAmount(sale.totalPrice, "COP");
    metrics.totalSales += 1;
  }

  for (const country of ["Colombia", "USA"] as const) {
    const metrics = comparison[country];
    if (metrics.totalLocations === 0) continue;
    metrics.averageRevenuePerLocation.USD = roundToTwoDecimals(
      metrics.totalRevenue.USD / metrics.totalLocations,
    );
    metrics.averageRevenuePerLocation.COP = roundToTwoDecimals(
      metrics.totalRevenue.COP / metrics.totalLocations,
    );
    metrics.totalRevenue.USD = roundToTwoDecimals(metrics.totalRevenue.USD);
    metrics.totalRevenue.COP = roundToTwoDecimals(metrics.totalRevenue.COP);
  }

  return comparison;
}