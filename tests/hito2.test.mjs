import assert from "node:assert/strict";
import test from "node:test";
import {
  filterActiveLocations,
  filterMenuItemsByCategory,
  filterSalesByDateRange,
  filterSalesByItemId,
  filterSalesByLocation,
  sortLocationsByCapacity,
  sortMenuItemsByPrice,
} from "../src/utils/collections.ts";
import {
  binarySearchLocationByCapacity,
  findLocationById,
  findMenuItemByName,
} from "../src/utils/search.ts";
import {
  calculateAverageTicket,
  calculateCountryComparison,
  calculateDailyRevenue,
  calculateLocationMargin,
  calculateWasteCost,
  convertCurrency,
  countBy,
  countSalesByPaymentMethod,
  averageBy,
  findTopSellingItems,
  groupWasteByReason,
  maxBy,
  minBy,
  rankLocationsByPerformance,
  scoreLocationPerformance,
  sumBy,
} from "../src/utils/transformations.ts";
import {
  validateLocation,
  validateMenuItem,
  validateSaleTransaction,
} from "../src/utils/validations.ts";

const menuItems = [
  {
    id: "ITEM-PICANHA-250",
    name: "Picanha 250g",
    category: "Meat",
    basePrice: { USD: 18.5, COP: 74000 },
    ingredientCost: { USD: 7.2, COP: 28800 },
    prepTimeMinutes: 15,
    isAvailableInColombia: true,
    isAvailableInUSA: true,
    allergens: [],
    status: "Active",
  },
  {
    id: "ITEM-FRIES",
    name: "Papas Fritas",
    category: "Side",
    basePrice: { USD: 4.5, COP: 18000 },
    ingredientCost: { USD: 1.2, COP: 4800 },
    prepTimeMinutes: 8,
    isAvailableInColombia: true,
    isAvailableInUSA: true,
    allergens: [],
    status: "Active",
  },
  {
    id: "ITEM-COKE",
    name: "Coca-Cola",
    category: "Beverage",
    basePrice: { USD: 2.5, COP: 10000 },
    ingredientCost: { USD: 0.8, COP: 3200 },
    prepTimeMinutes: 2,
    isAvailableInColombia: true,
    isAvailableInUSA: true,
    allergens: [],
    status: "Seasonal",
  },
];

const locations = [
  {
    id: "LOC-MEDELLIN-01",
    name: "Brasaland Medellín Centro",
    city: "Medellín",
    country: "Colombia",
    openingYear: 2008,
    seatingCapacity: 80,
    staffCount: 12,
    monthlyRentCost: { USD: 1500, COP: 6000000 },
    averageMonthlyUtilities: { USD: 400, COP: 1600000 },
    manager: "Carlos Jiménez",
    status: "Active",
  },
  {
    id: "LOC-MIAMI-01",
    name: "Brasaland Miami Beach",
    city: "Miami",
    country: "USA",
    openingYear: 2018,
    seatingCapacity: 100,
    staffCount: 15,
    monthlyRentCost: { USD: 5500, COP: 22000000 },
    averageMonthlyUtilities: { USD: 800, COP: 3200000 },
    manager: "Jake Morrison",
    status: "Active",
  },
  {
    id: "LOC-CALI-01",
    name: "Brasaland Cali",
    city: "Cali",
    country: "Colombia",
    openingYear: 2020,
    seatingCapacity: 50,
    staffCount: 10,
    monthlyRentCost: { USD: 1000, COP: 4000000 },
    averageMonthlyUtilities: { USD: 300, COP: 1200000 },
    manager: "Ana Torres",
    status: "Temporarily closed",
  },
];

const sales = [
  {
    id: "TXN-2024-15482",
    locationId: "LOC-MEDELLIN-01",
    itemId: "ITEM-PICANHA-250",
    quantity: 2,
    totalPrice: { USD: 37, COP: 148000 },
    paymentMethod: "Credit card",
    timestamp: new Date("2024-03-15T19:30:00Z"),
    waiterName: "María González",
  },
  {
    id: "TXN-2024-15483",
    locationId: "LOC-MIAMI-01",
    itemId: "ITEM-FRIES",
    quantity: 3,
    totalPrice: { USD: 13.5, COP: 54000 },
    paymentMethod: "Cash",
    timestamp: new Date("2024-03-15T20:15:00Z"),
    waiterName: "John Smith",
  },
  {
    id: "TXN-2024-15484",
    locationId: "LOC-MEDELLIN-01",
    itemId: "ITEM-COKE",
    quantity: 1,
    totalPrice: { USD: 2.5, COP: 10000 },
    paymentMethod: "Digital wallet",
    timestamp: new Date("2024-03-16T00:00:00Z"),
    waiterName: "María González",
  },
];

const wasteRecords = [
  {
    id: "WASTE-1",
    locationId: "LOC-MEDELLIN-01",
    itemId: "ITEM-PICANHA-250",
    quantity: 1,
    reason: "Expired",
    cost: { USD: 7.2, COP: 28800 },
    timestamp: new Date("2024-03-15T21:00:00Z"),
    reportedBy: "María González",
  },
  {
    id: "WASTE-2",
    locationId: "LOC-MIAMI-01",
    itemId: "ITEM-FRIES",
    quantity: 1,
    reason: "Cooking error",
    cost: { USD: 1.2, COP: 4800 },
    timestamp: new Date("2024-03-15T21:00:00Z"),
    reportedBy: "John Smith",
  },
];

test("collection filters include date boundaries and return expected records", () => {
  assert.deepEqual(filterSalesByLocation(sales, "LOC-MEDELLIN-01").map((sale) => sale.id), [
    "TXN-2024-15482",
    "TXN-2024-15484",
  ]);
  assert.deepEqual(
    filterSalesByDateRange(sales, new Date("2024-03-15T19:30:00Z"), new Date("2024-03-15T20:15:00Z"))
      .map((sale) => sale.id),
    ["TXN-2024-15482", "TXN-2024-15483"],
  );
  assert.deepEqual(filterSalesByDateRange(sales, new Date("invalid"), new Date()), []);
  assert.deepEqual(filterMenuItemsByCategory(menuItems, "Meat").map((item) => item.id), ["ITEM-PICANHA-250"]);
  assert.deepEqual(filterActiveLocations(locations).map((location) => location.id), ["LOC-MEDELLIN-01", "LOC-MIAMI-01"]);
  assert.deepEqual(filterSalesByLocation([], "missing"), []);
  assert.deepEqual(filterSalesByItemId(sales, "ITEM-FRIES"), [sales[1]]);
  assert.deepEqual(filterSalesByLocation([null, sales[0]], "LOC-MEDELLIN-01"), [sales[0]]);
  assert.deepEqual(filterMenuItemsByCategory([null, menuItems[0]], "Meat"), [menuItems[0]]);
});

test("sorting returns ordered copies without mutating input arrays", () => {
  const originalLocations = [...locations];
  assert.deepEqual(sortLocationsByCapacity(locations, "asc").map((location) => location.seatingCapacity), [50, 80, 100]);
  assert.deepEqual(sortLocationsByCapacity(locations, "desc").map((location) => location.seatingCapacity), [100, 80, 50]);
  assert.deepEqual(sortMenuItemsByPrice(menuItems, "COP", "asc").map((item) => item.basePrice.COP), [10000, 18000, 74000]);
  assert.deepEqual(locations, originalLocations);
  assert.notEqual(sortLocationsByCapacity(locations, "asc"), locations);
});

test("linear and binary searches find values and handle misses", () => {
  assert.equal(findLocationById(locations, "LOC-MIAMI-01"), locations[1]);
  assert.equal(findLocationById(locations, "missing"), null);
  assert.equal(findMenuItemByName(menuItems, "  pApAs FrItAs  "), menuItems[1]);
  assert.equal(findMenuItemByName(menuItems, "missing"), null);
  const sortedLocations = sortLocationsByCapacity(locations, "asc");
  assert.equal(sortedLocations[binarySearchLocationByCapacity(sortedLocations, 80)].seatingCapacity, 80);
  assert.equal(binarySearchLocationByCapacity(sortedLocations, 81), -1);
  assert.equal(binarySearchLocationByCapacity([], 80), -1);
  assert.equal(findLocationById([null, ...locations], "LOC-MIAMI-01"), locations[1]);
  assert.equal(findMenuItemByName([null, ...menuItems], "Picanha 250g"), menuItems[0]);
});

test("financial calculations keep currencies separate and round to cents", () => {
  assert.equal(calculateDailyRevenue(sales, new Date("2024-03-15T00:00:00Z"), "USD"), 50.5);
  assert.equal(calculateDailyRevenue(sales, new Date("2024-03-15T00:00:00Z"), "COP"), 202000);
  assert.equal(calculateDailyRevenue(sales, new Date("2024-03-15T00:00:00Z"), "USD", "America/Bogota"), 53);
  assert.equal(calculateDailyRevenue(sales, new Date("2024-03-15T00:00:00Z"), "USD", "Invalid/Timezone"), 0);
  assert.equal(calculateLocationMargin(sales, menuItems, "LOC-MEDELLIN-01", "USD"), 61.52);
  assert.equal(calculateWasteCost(wasteRecords, "LOC-MEDELLIN-01", "COP"), 28800);
  assert.equal(convertCurrency(1.235, "USD", "COP"), 4940);
  assert.equal(convertCurrency(999, "COP", "USD"), 0.25);
  assert.equal(convertCurrency(12.345, "USD", "USD"), 12.345);
  assert.equal(calculateAverageTicket(sales, "USD"), 17.67);
  assert.equal(calculateAverageTicket([], "USD"), 0);
});

test("location performance is bounded and ranking is descending", () => {
  const location = {
    ...locations[0],
    id: "LOC-SCORE-01",
    openingYear: 2026,
    seatingCapacity: 10,
  };
  const scoreMenu = [{
    ...menuItems[0],
    ingredientCost: { USD: 500, COP: 2000000 },
  }];
  const scoreSale = {
    ...sales[0],
    locationId: location.id,
    itemId: scoreMenu[0].id,
    quantity: 1,
    totalPrice: { USD: 1000, COP: 4000000 },
  };
  const scoreWaste = [{
    ...wasteRecords[0],
    locationId: location.id,
    cost: { USD: 500, COP: 2000000 },
  }];
  assert.equal(scoreLocationPerformance(location, [scoreSale], scoreWaste, scoreMenu, new Date("2026-01-02T00:00:00Z")), 48);
  assert.equal(scoreLocationPerformance(location, [], [], scoreMenu, new Date("2026-01-02T00:00:00Z")), 0);
  const ranked = rankLocationsByPerformance([locations[1], location], [scoreSale], scoreWaste, scoreMenu, new Date("2026-01-02T00:00:00Z"));
  assert.equal(ranked[0].location.id, location.id);
  assert.ok(ranked.every(({ score }) => score >= 0 && score <= 100));
  assert.equal(rankLocationsByPerformance([null, location], [], [], [], new Date("2026-01-02T00:00:00Z")).length, 1);
});

test("aggregations include empty categories and compare countries without currency conversion", () => {
  assert.deepEqual(countBy(menuItems, (item) => item.category), { Meat: 1, Side: 1, Beverage: 1 });
  assert.equal(sumBy(sales, (sale) => sale.quantity), 6);
  assert.equal(averageBy(menuItems, (item) => item.basePrice.USD), 8.5);
  assert.equal(maxBy(sales, (sale) => sale.totalPrice.USD), sales[0]);
  assert.equal(minBy(sales, (sale) => sale.totalPrice.USD), sales[2]);
  assert.equal(maxBy([], () => 0), null);
  assert.equal(minBy([null], () => 0), null);
  assert.equal(averageBy([1, Number.NaN, 3], (value) => value), 2);
  assert.deepEqual(countSalesByPaymentMethod(sales), {
    Cash: 1,
    "Credit card": 1,
    "Debit card": 0,
    "Digital wallet": 1,
  });
  assert.deepEqual(findTopSellingItems(sales, menuItems, 2).map(({ item, totalSold }) => [item.id, totalSold]), [
    ["ITEM-PICANHA-250", 2],
    ["ITEM-FRIES", 3],
  ].sort((left, right) => right[1] - left[1]));
  const groupedWaste = groupWasteByReason(wasteRecords);
  assert.equal(groupedWaste.Expired.length, 1);
  assert.equal(groupedWaste.Damage.length, 0);
  assert.equal(Object.keys(groupedWaste).length, 5);

  const comparison = calculateCountryComparison(sales, locations, menuItems);
  assert.deepEqual(comparison.Colombia, {
    totalLocations: 2,
    totalRevenue: { USD: 39.5, COP: 158000 },
    averageRevenuePerLocation: { USD: 19.75, COP: 79000 },
    totalSales: 2,
  });
  assert.deepEqual(comparison.USA, {
    totalLocations: 1,
    totalRevenue: { USD: 13.5, COP: 54000 },
    averageRevenuePerLocation: { USD: 13.5, COP: 54000 },
    totalSales: 1,
  });
  assert.equal(calculateAverageTicket([null, sales[0]], "USD"), 37);
  assert.equal(calculateDailyRevenue([null, sales[0]], new Date("2024-03-15T00:00:00Z"), "USD"), 37);
  assert.deepEqual(groupWasteByReason([null, ...wasteRecords]).Expired, [wasteRecords[0]]);
  assert.equal(calculateCountryComparison([null, ...sales], [null, ...locations], [null, ...menuItems]).Colombia.totalSales, 2);
});

test("business validators accept valid objects and reject invalid boundaries", () => {
  assert.equal(validateMenuItem(null).valid, false);
  assert.equal(validateSaleTransaction(null).valid, false);
  assert.equal(validateLocation(null, 2026).valid, false);
  assert.deepEqual(validateMenuItem(menuItems[0]), { valid: true, errors: [] });
  assert.equal(validateMenuItem({ ...menuItems[0], prepTimeMinutes: 61 }).valid, false);
  assert.equal(validateMenuItem({ ...menuItems[0], isAvailableInColombia: false, isAvailableInUSA: false }).valid, false);
  assert.equal(validateMenuItem({ ...menuItems[0], isAvailableInColombia: "yes" }).valid, false);

  assert.deepEqual(validateSaleTransaction(sales[0]), { valid: true, errors: [] });
  assert.equal(validateSaleTransaction({ ...sales[0], quantity: 0 }).valid, false);
  assert.equal(validateSaleTransaction({ ...sales[0], timestamp: new Date("invalid") }).valid, false);

  assert.deepEqual(validateLocation(locations[0], 2026), { valid: true, errors: [] });
  assert.equal(validateLocation({ ...locations[0], openingYear: 2007 }, 2026).valid, false);
  assert.equal(validateLocation({ ...locations[0], staffCount: 0 }, 2026).valid, false);
  assert.equal(validateLocation(locations[0], Number.NaN).valid, false);
});
