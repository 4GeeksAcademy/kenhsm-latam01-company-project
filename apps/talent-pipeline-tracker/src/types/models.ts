export type CountryCode = "CO" | "US";

export type CurrencyCode = "COP" | "USD";

export interface RestaurantBranch {
  id: string;
  name: string;
  city: string;
  country: CountryCode;
  timezone: string;
  openedAtISO: string;
  isActive: boolean;
}

export interface DailySalesSnapshot {
  id: string;
  branchId: string;
  businessDateISO: string;
  currency: CurrencyCode;
  ordersCount: number;
  revenueAmount: number;
  averageTicketAmount: number;
  serviceStartISO: string;
  serviceEndISO: string;
}

export interface SupplierPriceEntry {
  supplierId: string;
  supplierName: string;
  category: "protein" | "vegetables" | "packaging" | "beverages" | "cleaning";
  itemName: string;
  unit: "kg" | "unit" | "box" | "liter";
  unitPrice: number;
  currency: CurrencyCode;
  effectiveDateISO: string;
}

export interface BranchDisplayLabel {
  branchId: string;
  branchName: string;
  city: string;
  country: CountryCode;
}

export const BRANCH_OPENING_HOUR = 9;
export const BRANCH_CLOSING_HOUR = 23;

export function toBranchDisplayLabel(branch: RestaurantBranch): BranchDisplayLabel {
  return {
    branchId: branch.id,
    branchName: branch.name,
    city: branch.city,
    country: branch.country,
  };
}

export function calculateAverageTicket(snapshot: DailySalesSnapshot): number {
  if (snapshot.ordersCount <= 0) {
    return 0;
  }

  return snapshot.revenueAmount / snapshot.ordersCount;
}

export function isBranchOpenAtISO(
  snapshot: DailySalesSnapshot,
  timestampISO: string,
): boolean {
  const start = Date.parse(snapshot.serviceStartISO);
  const end = Date.parse(snapshot.serviceEndISO);
  const current = Date.parse(timestampISO);

  if (Number.isNaN(start) || Number.isNaN(end) || Number.isNaN(current)) {
    return false;
  }

  return current >= start && current <= end;
}

export function convertRevenue(
  snapshot: DailySalesSnapshot,
  exchangeRateCopPerUsd: number,
): { revenueCOP: number; revenueUSD: number } {
  if (exchangeRateCopPerUsd <= 0) {
    return { revenueCOP: 0, revenueUSD: 0 };
  }

  if (snapshot.currency === "COP") {
    return {
      revenueCOP: snapshot.revenueAmount,
      revenueUSD: snapshot.revenueAmount / exchangeRateCopPerUsd,
    };
  }

  return {
    revenueCOP: snapshot.revenueAmount * exchangeRateCopPerUsd,
    revenueUSD: snapshot.revenueAmount,
  };
}

export const sampleRestaurantBranch: RestaurantBranch = {
  id: "br-co-medellin-centro",
  name: "Brasaland Centro",
  city: "Medellin",
  country: "CO",
  timezone: "America/Bogota",
  openedAtISO: "2013-02-01T10:00:00.000Z",
  isActive: true,
};

export const sampleDailySalesSnapshot: DailySalesSnapshot = {
  id: "sales-2026-08-06-br-co-medellin-centro",
  branchId: "br-co-medellin-centro",
  businessDateISO: "2026-08-06",
  currency: "COP",
  ordersCount: 215,
  revenueAmount: 11825000,
  averageTicketAmount: 55000,
  serviceStartISO: "2026-08-06T11:00:00.000Z",
  serviceEndISO: "2026-08-06T23:00:00.000Z",
};

export const sampleSupplierPriceEntry: SupplierPriceEntry = {
  supplierId: "sup-001",
  supplierName: "Andes Protein Distribution",
  category: "protein",
  itemName: "beef patty 150g",
  unit: "kg",
  unitPrice: 38500,
  currency: "COP",
  effectiveDateISO: "2026-08-01",
};
