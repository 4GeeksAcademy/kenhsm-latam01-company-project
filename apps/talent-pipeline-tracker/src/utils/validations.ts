import {
  DailySalesSnapshot,
  RestaurantBranch,
  SupplierPriceEntry,
  calculateAverageTicket,
} from "@/src/types/models";

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

function isNonEmptyText(value: string): boolean {
  return value.trim().length > 0;
}

function isValidISODate(value: string): boolean {
  return !Number.isNaN(Date.parse(value));
}

function isValidBusinessDate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && isValidISODate(`${value}T00:00:00.000Z`);
}

export function validateRestaurantBranch(branch: RestaurantBranch): ValidationResult {
  const errors: string[] = [];

  if (!isNonEmptyText(branch.id)) {
    errors.push("Branch id is required");
  }

  if (!isNonEmptyText(branch.name)) {
    errors.push("Branch name is required");
  }

  if (!isNonEmptyText(branch.city)) {
    errors.push("Branch city is required");
  }

  if (branch.country !== "CO" && branch.country !== "US") {
    errors.push("Branch country must be CO or US");
  }

  if (!isNonEmptyText(branch.timezone)) {
    errors.push("Branch timezone is required");
  }

  if (!isValidISODate(branch.openedAtISO)) {
    errors.push("Branch openedAtISO must be a valid ISO date");
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

export function validateDailySalesSnapshot(snapshot: DailySalesSnapshot): ValidationResult {
  const errors: string[] = [];

  if (!isNonEmptyText(snapshot.id)) {
    errors.push("Snapshot id is required");
  }

  if (!isNonEmptyText(snapshot.branchId)) {
    errors.push("Snapshot branchId is required");
  }

  if (!isValidBusinessDate(snapshot.businessDateISO)) {
    errors.push("Snapshot businessDateISO must use YYYY-MM-DD format");
  }

  if (snapshot.currency !== "COP" && snapshot.currency !== "USD") {
    errors.push("Snapshot currency must be COP or USD");
  }

  if (!Number.isFinite(snapshot.ordersCount) || snapshot.ordersCount < 0) {
    errors.push("ordersCount must be a non-negative number");
  }

  if (!Number.isFinite(snapshot.revenueAmount) || snapshot.revenueAmount < 0) {
    errors.push("revenueAmount must be a non-negative number");
  }

  if (!Number.isFinite(snapshot.averageTicketAmount) || snapshot.averageTicketAmount < 0) {
    errors.push("averageTicketAmount must be a non-negative number");
  }

  const computedAverage = calculateAverageTicket(snapshot);
  if (snapshot.ordersCount > 0) {
    const difference = Math.abs(snapshot.averageTicketAmount - computedAverage);
    if (difference > 0.01) {
      errors.push("averageTicketAmount must match revenueAmount / ordersCount");
    }
  }

  if (snapshot.ordersCount === 0 && snapshot.revenueAmount !== 0) {
    errors.push("revenueAmount must be 0 when ordersCount is 0");
  }

  if (!isValidISODate(snapshot.serviceStartISO) || !isValidISODate(snapshot.serviceEndISO)) {
    errors.push("serviceStartISO and serviceEndISO must be valid ISO dates");
  } else {
    const start = Date.parse(snapshot.serviceStartISO);
    const end = Date.parse(snapshot.serviceEndISO);
    if (end < start) {
      errors.push("serviceEndISO must be after serviceStartISO");
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

export function validateSupplierPriceEntry(entry: SupplierPriceEntry): ValidationResult {
  const errors: string[] = [];

  if (!isNonEmptyText(entry.supplierId)) {
    errors.push("supplierId is required");
  }

  if (!isNonEmptyText(entry.supplierName)) {
    errors.push("supplierName is required");
  }

  if (!isNonEmptyText(entry.itemName)) {
    errors.push("itemName is required");
  }

  if (!Number.isFinite(entry.unitPrice) || entry.unitPrice <= 0) {
    errors.push("unitPrice must be greater than 0");
  }

  if (entry.currency !== "COP" && entry.currency !== "USD") {
    errors.push("currency must be COP or USD");
  }

  if (!isValidBusinessDate(entry.effectiveDateISO)) {
    errors.push("effectiveDateISO must use YYYY-MM-DD format");
  } else {
    const effectiveDate = new Date(`${entry.effectiveDateISO}T00:00:00.000Z`);
    const today = new Date();
    today.setUTCHours(0, 0, 0, 0);

    if (effectiveDate.getTime() > today.getTime()) {
      errors.push("effectiveDateISO cannot be in the future");
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}
