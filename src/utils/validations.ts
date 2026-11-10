import type {
  Location,
  LocationStatus,
  MenuCategory,
  MenuItem,
  MenuItemStatus,
  PaymentMethod,
  Price,
  SaleTransaction,
  ValidationResult,
} from "../types/models.ts";

const menuCategories: MenuCategory[] = ["Meat", "Side", "Beverage", "Dessert", "Combo"];
const menuItemStatuses: MenuItemStatus[] = ["Active", "Seasonal", "Discontinued"];
const paymentMethods: PaymentMethod[] = ["Cash", "Credit card", "Debit card", "Digital wallet"];
const locationStatuses: LocationStatus[] = ["Active", "Temporarily closed", "Under renovation"];

function isNonEmptyText(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isPositivePrice(price: Price | null | undefined): boolean {
  return Boolean(
    price &&
      Number.isFinite(price.USD) && price.USD > 0 &&
      Number.isFinite(price.COP) && price.COP > 0,
  );
}

function createResult(errors: string[]): ValidationResult {
  return { valid: errors.length === 0, errors };
}

export function validateMenuItem(item: MenuItem): ValidationResult {
  const errors: string[] = [];
  if (!item || typeof item !== "object") return createResult(["Menu item is required"]);

  if (!isNonEmptyText(item.id)) errors.push("Menu item id is required");
  if (!isNonEmptyText(item.name)) errors.push("Menu item name must not be empty");
  if (!menuCategories.includes(item.category)) errors.push("Menu item category is invalid");
  if (!isPositivePrice(item.basePrice)) errors.push("Base price must be greater than 0 in USD and COP");
  if (!isPositivePrice(item.ingredientCost)) errors.push("Ingredient cost must be greater than 0 in USD and COP");
  if (!Number.isFinite(item.prepTimeMinutes) || item.prepTimeMinutes <= 0 || item.prepTimeMinutes > 60) {
    errors.push("Preparation time must be greater than 0 and at most 60 minutes");
  }
  if (typeof item.isAvailableInColombia !== "boolean" || typeof item.isAvailableInUSA !== "boolean") {
    errors.push("Country availability values must be booleans");
  }
  if (item.isAvailableInColombia !== true && item.isAvailableInUSA !== true) {
    errors.push("Menu item must be available in at least one country");
  }
  if (!Array.isArray(item.allergens) || item.allergens.some((allergen) => !isNonEmptyText(allergen))) {
    errors.push("Allergens must be an array of non-empty strings");
  }
  if (!menuItemStatuses.includes(item.status)) errors.push("Menu item status is invalid");

  return createResult(errors);
}

export function validateSaleTransaction(sale: SaleTransaction): ValidationResult {
  const errors: string[] = [];
  if (!sale || typeof sale !== "object") return createResult(["Sale transaction is required"]);

  if (!isNonEmptyText(sale.id)) errors.push("Sale id is required");
  if (!isNonEmptyText(sale.locationId)) errors.push("Sale locationId is required");
  if (!isNonEmptyText(sale.itemId)) errors.push("Sale itemId is required");
  if (!Number.isFinite(sale.quantity) || sale.quantity <= 0) errors.push("Sale quantity must be greater than 0");
  if (!isPositivePrice(sale.totalPrice)) errors.push("Sale prices must be greater than 0 in USD and COP");
  if (!paymentMethods.includes(sale.paymentMethod)) errors.push("Sale payment method is invalid");
  if (!(sale.timestamp instanceof Date) || !Number.isFinite(sale.timestamp.getTime())) {
    errors.push("Sale timestamp must be a valid date");
  }
  if (!isNonEmptyText(sale.waiterName)) errors.push("Waiter name must not be empty");

  return createResult(errors);
}

export function validateLocation(
  location: Location,
  currentYear: number = new Date().getFullYear(),
): ValidationResult {
  const errors: string[] = [];
  if (!location || typeof location !== "object") return createResult(["Location is required"]);

  if (!Number.isInteger(currentYear)) errors.push("Current year must be an integer");
  if (!isNonEmptyText(location.id)) errors.push("Location id is required");
  if (!isNonEmptyText(location.name)) errors.push("Location name is required");
  if (!isNonEmptyText(location.city)) errors.push("Location city is required");
  if (location.country !== "Colombia" && location.country !== "USA") errors.push("Location country is invalid");
  if (!Number.isInteger(location.openingYear) || location.openingYear < 2008 || location.openingYear > currentYear) {
    errors.push(`Opening year must be between 2008 and ${currentYear}`);
  }
  if (!Number.isFinite(location.seatingCapacity) || location.seatingCapacity <= 0) {
    errors.push("Seating capacity must be greater than 0");
  }
  if (!Number.isFinite(location.staffCount) || location.staffCount <= 0) {
    errors.push("Staff count must be greater than 0");
  }
  if (!isPositivePrice(location.monthlyRentCost)) errors.push("Monthly rent must be greater than 0 in USD and COP");
  if (!isPositivePrice(location.averageMonthlyUtilities)) {
    errors.push("Average monthly utilities must be greater than 0 in USD and COP");
  }
  if (!isNonEmptyText(location.manager)) errors.push("Location manager is required");
  if (!locationStatuses.includes(location.status)) errors.push("Location status is invalid");

  return createResult(errors);
}