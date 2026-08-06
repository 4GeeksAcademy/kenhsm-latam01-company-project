import { CountryCode, DailySalesSnapshot, RestaurantBranch } from "@/src/types/models";

export function countByCategory<T, K extends PropertyKey>(
  collection: readonly T[],
  keySelector: (item: T) => K,
): Record<K, number> {
  return collection.reduce<Record<K, number>>((accumulator, item) => {
    const key = keySelector(item);
    const currentCount = accumulator[key] ?? 0;
    accumulator[key] = currentCount + 1;
    return accumulator;
  }, {} as Record<K, number>);
}

export function sumBy<T>(collection: readonly T[], valueSelector: (item: T) => number): number {
  return collection.reduce((accumulator, item) => accumulator + valueSelector(item), 0);
}

export function averageBy<T>(collection: readonly T[], valueSelector: (item: T) => number): number {
  if (collection.length === 0) {
    return 0;
  }

  const total = sumBy(collection, valueSelector);
  return total / collection.length;
}

export function maxBy<T>(collection: readonly T[], valueSelector: (item: T) => number): T | null {
  if (collection.length === 0) {
    return null;
  }

  return collection.reduce((currentMax, item) => {
    if (valueSelector(item) > valueSelector(currentMax)) {
      return item;
    }

    return currentMax;
  });
}

export function minBy<T>(collection: readonly T[], valueSelector: (item: T) => number): T | null {
  if (collection.length === 0) {
    return null;
  }

  return collection.reduce((currentMin, item) => {
    if (valueSelector(item) < valueSelector(currentMin)) {
      return item;
    }

    return currentMin;
  });
}

export interface DailySalesReport {
  totalBranchesReported: number;
  totalOrders: number;
  totalRevenue: number;
  averageTicketAcrossBranches: number;
  bestRevenueBranchId: string | null;
  lowestRevenueBranchId: string | null;
  recordsByCountry: Record<CountryCode, number>;
}

export function buildDailySalesReport(
  snapshots: readonly DailySalesSnapshot[],
  branches: readonly RestaurantBranch[],
): DailySalesReport {
  if (snapshots.length === 0) {
    return {
      totalBranchesReported: 0,
      totalOrders: 0,
      totalRevenue: 0,
      averageTicketAcrossBranches: 0,
      bestRevenueBranchId: null,
      lowestRevenueBranchId: null,
      recordsByCountry: { CO: 0, US: 0 },
    };
  }

  const totalOrders = sumBy(snapshots, (snapshot) => snapshot.ordersCount);
  const totalRevenue = sumBy(snapshots, (snapshot) => snapshot.revenueAmount);
  const averageTicketAcrossBranches = averageBy(
    snapshots,
    (snapshot) => snapshot.averageTicketAmount,
  );

  const bestRevenueSnapshot = maxBy(snapshots, (snapshot) => snapshot.revenueAmount);
  const lowestRevenueSnapshot = minBy(snapshots, (snapshot) => snapshot.revenueAmount);

  const branchCountryMap = branches.reduce<Record<string, CountryCode>>((accumulator, branch) => {
    accumulator[branch.id] = branch.country;
    return accumulator;
  }, {});

  const recordsByCountry = snapshots.reduce<Record<CountryCode, number>>(
    (accumulator, snapshot) => {
      const country = branchCountryMap[snapshot.branchId];
      if (country === "CO" || country === "US") {
        accumulator[country] += 1;
      }
      return accumulator;
    },
    { CO: 0, US: 0 },
  );

  return {
    totalBranchesReported: snapshots.length,
    totalOrders,
    totalRevenue,
    averageTicketAcrossBranches,
    bestRevenueBranchId: bestRevenueSnapshot?.branchId ?? null,
    lowestRevenueBranchId: lowestRevenueSnapshot?.branchId ?? null,
    recordsByCountry,
  };
}
