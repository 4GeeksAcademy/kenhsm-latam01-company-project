/**
 * inventory.js
 * 
 * Módulo centralizado para todas las llamadas a los endpoints /inventory de la API.
 * Ningún componente debe llamar a fetch directamente para inventario.
 */

const tokenKey = "brasaland_access_token";

/**
 * Obtiene el token JWT del localStorage
 */
function getAuthToken() {
  return localStorage.getItem(tokenKey);
}

/**
 * Obtiene la URL base de la API desde la configuración
 */
export async function getApiBase() {
  try {
    const { loadPublicConfig } = await import("./runtime-config.mjs");
    const runtimeConfig = await loadPublicConfig();
    return runtimeConfig.NEXT_PUBLIC_INVENTORY_API_URL || "http://127.0.0.1:8000";
  } catch {
    return "http://127.0.0.1:8000";
  }
}

/**
 * Maneja errores de la API
 * Extrae el mensaje de error del cuerpo de la respuesta
 */
function parseError(response) {
  if (response.status === 401) {
    return { message: "No autenticado. Por favor, inicia sesión.", status: 401 };
  }
  if (response.status === 403) {
    return { message: "No autorizado para esta acción.", status: 403 };
  }
  if (response.status === 400) {
    return { message: "Solicitud inválida. Verifica los datos e intenta de nuevo.", status: 400 };
  }
  if (response.status >= 500) {
    return { message: "Error del servidor. Intenta más tarde.", status: response.status };
  }
  return { message: "Error desconocido.", status: response.status };
}

/**
 * GET /inventory/products
 * Lista todos los ingredientes con su stock actual
 */
export async function getProducts() {
  try {
    const apiBase = await getApiBase();
    const response = await fetch(`${apiBase}/inventory/products`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const error = parseError(response);
      throw new Error(error.message);
    }

    const data = await response.json();
    return { success: true, data: data.items || [], total: data.total || 0 };
  } catch (error) {
    console.error("Error fetching products:", error);
    return { success: false, error: error.message };
  }
}

/**
 * GET /inventory/products/{id}
 * Obtiene un ingrediente individual
 */
export async function getProductById(id) {
  try {
    const apiBase = await getApiBase();
    const response = await fetch(`${apiBase}/inventory/products/${id}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const error = parseError(response);
      throw new Error(error.message);
    }

    return { success: true, data: await response.json() };
  } catch (error) {
    console.error("Error fetching product:", error);
    return { success: false, error: error.message };
  }
}

/**
 * POST /inventory/products
 * Crea un nuevo ingrediente (requiere autenticación)
 */
export async function createProduct(productData) {
  try {
    const token = getAuthToken();
    if (!token) {
      throw new Error("No autenticado. Por favor, inicia sesión.");
    }

    const apiBase = await getApiBase();
    const response = await fetch(`${apiBase}/inventory/products`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(productData),
    });

    if (!response.ok) {
      const error = parseError(response);
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || error.message);
    }

    return { success: true, data: await response.json() };
  } catch (error) {
    console.error("Error creating product:", error);
    return { success: false, error: error.message };
  }
}

/**
 * POST /inventory/orders/inbound
 * Registra una entrada de proveedor (requiere autenticación)
 */
export async function createInboundOrder(orderData) {
  try {
    const token = getAuthToken();
    if (!token) {
      throw new Error("No autenticado. Por favor, inicia sesión.");
    }

    const apiBase = await getApiBase();
    const response = await fetch(`${apiBase}/inventory/orders/inbound`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(orderData),
    });

    if (!response.ok) {
      const error = parseError(response);
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || error.message);
    }

    return { success: true, data: await response.json() };
  } catch (error) {
    console.error("Error creating inbound order:", error);
    return { success: false, error: error.message };
  }
}

/**
 * POST /inventory/orders/outbound
 * Registra una salida (consumo/merma) (requiere autenticación)
 */
export async function createOutboundOrder(orderData) {
  try {
    const token = getAuthToken();
    if (!token) {
      throw new Error("No autenticado. Por favor, inicia sesión.");
    }

    const apiBase = await getApiBase();
    const response = await fetch(`${apiBase}/inventory/orders/outbound`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(orderData),
    });

    if (!response.ok) {
      const error = parseError(response);
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || error.message);
    }

    return { success: true, data: await response.json() };
  } catch (error) {
    console.error("Error creating outbound order:", error);
    return { success: false, error: error.message };
  }
}

/**
 * GET /inventory/orders
 * Lista todas las órdenes (entradas y salidas)
 */
export async function getOrders() {
  try {
    const apiBase = await getApiBase();
    const response = await fetch(`${apiBase}/inventory/orders`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const error = parseError(response);
      throw new Error(error.message);
    }

    const data = await response.json();
    return {
      success: true,
      entries: data.entries || [],
      exits: data.exits || [],
    };
  } catch (error) {
    console.error("Error fetching orders:", error);
    return { success: false, error: error.message, entries: [], exits: [] };
  }
}
