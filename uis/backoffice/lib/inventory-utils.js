/**
 * inventory-utils.js
 * 
 * Utilidades para componentes de inventario
 */

const tokenKey = "brasaland_access_token";

/**
 * Verifica si el usuario está autenticado
 */
export function isAuthenticated() {
  return !!localStorage.getItem(tokenKey);
}

/**
 * Redirige a login si no está autenticado
 */
export function requireAuth(redirectTo = "/backoffice/inventory/products") {
  if (!isAuthenticated()) {
    window.location.href = "/backoffice/manager-chat.html";
    return false;
  }
  return true;
}

/**
 * Determina el nivel de stock basado en el valor actual
 * Retorna: "low", "medium", "high"
 * 
 * Umbrales:
 * - low: < 5 unidades (o porcentaje bajo)
 * - medium: 5-20 unidades
 * - high: > 20 unidades
 */
export function getStockLevel(currentStock) {
  if (currentStock <= 5) return "low";
  if (currentStock <= 20) return "medium";
  return "high";
}

/**
 * Obtiene el color CSS basado en el nivel de stock
 */
export function getStockColor(stockLevel) {
  switch (stockLevel) {
    case "low":
      return "#dc2626"; // red-600
    case "medium":
      return "#f59e0b"; // amber-500
    case "high":
      return "#16a34a"; // green-600
    default:
      return "#6b7280"; // gray-500
  }
}

/**
 * Obtiene la etiqueta de nivel de stock
 */
export function getStockLabel(stockLevel) {
  switch (stockLevel) {
    case "low":
      return "Bajo";
    case "medium":
      return "Medio";
    case "high":
      return "Alto";
    default:
      return "Desconocido";
  }
}

/**
 * Formatea una fecha para mostrar
 */
export function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleString("es-ES", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Categorías de ingredientes con etiquetas amigables
 */
export const categoryLabels = {
  meat: "Carne",
  produce: "Verdura",
  sauce: "Salsa",
  beverage: "Bebida",
  packaging: "Empaque",
  cleaning: "Limpieza",
};

/**
 * Países con etiquetas amigables
 */
export const countryLabels = {
  CO: "Colombia",
  US: "Estados Unidos",
};

/**
 * Razones de salida con etiquetas amigables
 */
export const exitReasonLabels = {
  consumption: "Consumo",
  waste: "Merma",
};
