/**
 * inventory-page.js
 * 
 * Controlador principal para todas las funcionalidades de inventario
 */

import {
  getProducts,
  getOrders,
  createInboundOrder,
  createOutboundOrder,
  getApiBase,
} from "../lib/inventory.js";
import {
  isAuthenticated,
  requireAuth,
  getStockLevel,
  getStockColor,
  getStockLabel,
  formatDate,
  categoryLabels,
  countryLabels,
  exitReasonLabels,
} from "../lib/inventory-utils.js";

// Estado global
let allProducts = [];
let currentUser = null;

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

async function initPage() {
  // Verificar autenticación
  if (!requireAuth()) return;

  // Obtener usuario
  const userDisplay = localStorage.getItem("brasaland_user_display") || "Usuario";
  currentUser = userDisplay;
  document.getElementById("userDisplay").textContent = userDisplay;

  // Configurar navegación
  setupNavigation();

  // Cargar productos y órdenes
  await loadProducts();
  await loadOrders();

  // Configurar formularios
  setupForms();
}

// ============================================================================
// NAVEGACIÓN
// ============================================================================

function setupNavigation() {
  const navLinks = document.querySelectorAll(".nav-link");

  navLinks.forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();

      // Remover clase active de todos los links
      navLinks.forEach((l) => l.classList.remove("active"));
      link.classList.add("active");

      // Ocultar todas las secciones
      const sections = document.querySelectorAll(".section");
      sections.forEach((s) => s.classList.remove("active"));

      // Mostrar sección seleccionada
      const sectionId = link.dataset.section;
      const section = document.getElementById(sectionId);
      if (section) {
        section.classList.add("active");

        // Si es la sección de órdenes, recargar
        if (sectionId === "orders") {
          loadOrders();
        }
      }
    });
  });
}

// ============================================================================
// PRODUCTOS
// ============================================================================

async function loadProducts() {
  const container = document.getElementById("productsContainer");
  const alertDiv = document.getElementById("productsAlert");

  container.innerHTML =
    '<div class="loading"><div class="spinner"></div><p>Cargando productos...</p></div>';
  alertDiv.innerHTML = "";

  const result = await getProducts();

  if (!result.success) {
    alertDiv.innerHTML = `<div class="alert alert-error">⚠️ ${result.error}</div>`;
    container.innerHTML = `<p style="color: #6b7280; text-align: center;">No se pudieron cargar los productos. Intenta de nuevo más tarde.</p>`;
    return;
  }

  allProducts = result.data;

  if (allProducts.length === 0) {
    container.innerHTML =
      '<p style="color: #6b7280; text-align: center;">No hay productos registrados.</p>';
    return;
  }

  // Renderizar tabla
  const table = createProductsTable(allProducts);
  container.innerHTML = "";
  container.appendChild(table);

  // Actualizar selects en formularios
  updateProductSelects();
}

function createProductsTable(products) {
  const table = document.createElement("table");
  table.className = "products-table";

  // Header
  const thead = document.createElement("thead");
  thead.innerHTML = `
    <tr>
      <th>SKU</th>
      <th>Nombre</th>
      <th>Categoría</th>
      <th>País</th>
      <th>Unidad</th>
      <th>Stock Actual</th>
      <th>Nivel</th>
    </tr>
  `;
  table.appendChild(thead);

  // Body
  const tbody = document.createElement("tbody");
  products.forEach((product) => {
    const stockLevel = getStockLevel(product.current_stock);
    const stockColor = getStockColor(stockLevel);
    const stockLabel = getStockLabel(stockLevel);

    const row = document.createElement("tr");
    row.innerHTML = `
      <td><strong>${product.sku}</strong></td>
      <td>${product.name}</td>
      <td>${categoryLabels[product.category] || product.category}</td>
      <td>${countryLabels[product.country_of_origin] || product.country_of_origin}</td>
      <td>${product.unit_of_measurement}</td>
      <td><strong>${product.current_stock.toFixed(2)}</strong></td>
      <td>
        <span class="stock-indicator" style="background-color: ${stockColor};"></span>
        ${stockLabel}
      </td>
    `;
    tbody.appendChild(row);
  });
  table.appendChild(tbody);

  return table;
}

function updateProductSelects() {
  const inboundSelect = document.getElementById("inboundProduct");
  const outboundSelect = document.getElementById("outboundProduct");

  // Limpiar opciones actuales (excepto la primera)
  while (inboundSelect.options.length > 1) {
    inboundSelect.remove(1);
  }
  while (outboundSelect.options.length > 1) {
    outboundSelect.remove(1);
  }

  // Agregar productos
  allProducts.forEach((product) => {
    const option1 = document.createElement("option");
    option1.value = product.id;
    option1.textContent = `${product.sku} - ${product.name}`;
    inboundSelect.appendChild(option1);

    const option2 = document.createElement("option");
    option2.value = product.id;
    option2.textContent = `${product.sku} - ${product.name}`;
    outboundSelect.appendChild(option2);
  });
}

// ============================================================================
// ÓRDENES
// ============================================================================

async function loadOrders() {
  const container = document.getElementById("ordersContainer");
  const alertDiv = document.getElementById("ordersAlert");

  container.innerHTML =
    '<div class="loading"><div class="spinner"></div><p>Cargando órdenes...</p></div>';
  alertDiv.innerHTML = "";

  const result = await getOrders();

  if (!result.success) {
    alertDiv.innerHTML = `<div class="alert alert-error">⚠️ ${result.error}</div>`;
    container.innerHTML = `<p style="color: #6b7280; text-align: center;">No se pudieron cargar las órdenes.</p>`;
    return;
  }

  const entries = result.entries || [];
  const exits = result.exits || [];

  if (entries.length === 0 && exits.length === 0) {
    container.innerHTML =
      '<p style="color: #6b7280; text-align: center;">No hay órdenes registradas.</p>';
    return;
  }

  // Combinar y ordenar por fecha descendente
  const allOrders = [...entries, ...exits].sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at)
  );

  const table = createOrdersTable(allOrders);
  container.innerHTML = "";
  container.appendChild(table);
}

function createOrdersTable(orders) {
  const table = document.createElement("table");
  table.className = "orders-table";

  const thead = document.createElement("thead");
  thead.innerHTML = `
    <tr>
      <th>Tipo</th>
      <th>SKU</th>
      <th>Producto</th>
      <th>Cantidad (kg)</th>
      <th>Razón/Proveedor</th>
      <th>Ubicación</th>
      <th>Usuario</th>
      <th>Fecha</th>
    </tr>
  `;
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  orders.forEach((order) => {
    const isEntry = "supplier_name" in order;
    const typeLabel = isEntry ? "Entrada" : "Salida";
    const typeBadgeClass = isEntry ? "badge-entry" : "badge-exit";
    const detail = isEntry ? order.supplier_name : exitReasonLabels[order.reason] || order.reason;

    const row = document.createElement("tr");
    row.innerHTML = `
      <td><span class="badge ${typeBadgeClass}">${typeLabel}</span></td>
      <td><strong>${order.ingredient.sku}</strong></td>
      <td>${order.ingredient.name}</td>
      <td>${order.quantity.toFixed(2)}</td>
      <td>${detail}</td>
      <td>${order.location_id}</td>
      <td>${order.user_uuid}</td>
      <td>${formatDate(order.created_at)}</td>
    `;
    tbody.appendChild(row);
  });
  table.appendChild(tbody);

  return table;
}

// ============================================================================
// FORMULARIOS
// ============================================================================

function setupForms() {
  // Formulario de entrada
  document.getElementById("inboundForm").addEventListener("submit", handleInboundSubmit);

  // Formulario de salida
  document.getElementById("outboundForm").addEventListener("submit", handleOutboundSubmit);

  // Monitor de producto en salida
  document.getElementById("outboundProduct").addEventListener("change", updateStockDisplay);
}

async function handleInboundSubmit(e) {
  e.preventDefault();

  const alertDiv = document.getElementById("inboundAlert");
  alertDiv.innerHTML = "";

  const productId = document.getElementById("inboundProduct").value;
  const quantity = parseFloat(document.getElementById("inboundQuantity").value);
  const supplierName = document.getElementById("inboundSupplier").value;
  const locationId = parseInt(document.getElementById("inboundLocation").value);

  if (!productId || !quantity || !supplierName || !locationId) {
    alertDiv.innerHTML = '<div class="alert alert-error">⚠️ Completa todos los campos obligatorios</div>';
    return;
  }

  // Encontrar el producto para obtener el usuario_uuid (placeholder por ahora)
  const product = allProducts.find((p) => p.id === parseInt(productId));
  if (!product) {
    alertDiv.innerHTML = '<div class="alert alert-error">⚠️ Producto no encontrado</div>';
    return;
  }

  const payload = {
    ingredient_id: parseInt(productId),
    quantity: quantity,
    supplier_name: supplierName,
    location_id: locationId,
    user_uuid: "user-001",
  };

  const result = await createInboundOrder(payload);

  if (result.success) {
    alertDiv.innerHTML =
      '<div class="alert alert-success">✅ Entrada registrada correctamente</div>';
    document.getElementById("inboundForm").reset();
    setTimeout(async () => {
      await loadProducts();
      await loadOrders();
    }, 1500);
  } else {
    alertDiv.innerHTML = `<div class="alert alert-error">❌ Error: ${result.error}</div>`;
  }
}

async function handleOutboundSubmit(e) {
  e.preventDefault();

  const alertDiv = document.getElementById("outboundAlert");
  alertDiv.innerHTML = "";

  const productId = document.getElementById("outboundProduct").value;
  const quantity = parseFloat(document.getElementById("outboundQuantity").value);
  const reason = document.querySelector('input[name="outboundReason"]:checked').value;
  const locationId = parseInt(document.getElementById("outboundLocation").value);

  if (!productId || !quantity || !locationId) {
    alertDiv.innerHTML = '<div class="alert alert-error">⚠️ Completa todos los campos obligatorios</div>';
    return;
  }

  const product = allProducts.find((p) => p.id === parseInt(productId));
  if (!product) {
    alertDiv.innerHTML = '<div class="alert alert-error">⚠️ Producto no encontrado</div>';
    return;
  }

  // Validación de stock en cliente
  if (quantity > product.current_stock) {
    alertDiv.innerHTML = `<div class="alert alert-warning">⚠️ Stock insuficiente. Disponible: ${product.current_stock.toFixed(2)} kg</div>`;
    return;
  }

  const payload = {
    ingredient_id: parseInt(productId),
    quantity: quantity,
    reason: reason,
    location_id: locationId,
    user_uuid: "user-001",
  };

  const result = await createOutboundOrder(payload);

  if (result.success) {
    alertDiv.innerHTML =
      '<div class="alert alert-success">✅ Salida registrada correctamente</div>';
    document.getElementById("outboundForm").reset();
    updateStockDisplay(); // Resetear display de stock
    setTimeout(async () => {
      await loadProducts();
      await loadOrders();
    }, 1500);
  } else {
    alertDiv.innerHTML = `<div class="alert alert-error">❌ Error: ${result.error}</div>`;
  }
}

function updateStockDisplay() {
  const productId = document.getElementById("outboundProduct").value;
  const stockDisplay = document.getElementById("stockDisplay");
  const stockValue = document.getElementById("stockValue");
  const stockWarning = document.getElementById("stockWarning");

  if (!productId) {
    stockValue.textContent = "-";
    stockWarning.textContent = "";
    return;
  }

  const product = allProducts.find((p) => p.id === parseInt(productId));
  if (!product) {
    stockValue.textContent = "Error";
    stockWarning.textContent = "";
    return;
  }

  const stockLevel = getStockLevel(product.current_stock);
  const stockColor = getStockColor(stockLevel);

  stockValue.textContent = `${product.current_stock.toFixed(2)} kg`;
  stockValue.style.color = stockColor;

  if (stockLevel === "low") {
    stockWarning.textContent = "⚠️ Stock bajo - considera una entrada pronto";
  } else if (stockLevel === "medium") {
    stockWarning.textContent = "ℹ️ Stock medio";
  } else {
    stockWarning.textContent = "✓ Stock disponible";
  }
}

// ============================================================================
// UTILIDADES
// ============================================================================

function logout() {
  localStorage.removeItem("brasaland_access_token");
  localStorage.removeItem("brasaland_user_display");
  window.location.href = "/backoffice";
}

// ============================================================================
// INICIAR
// ============================================================================

initPage().catch((error) => {
  console.error("Error al inicializar página:", error);
  const alert = document.querySelector(".inventory-content");
  if (alert) {
    alert.innerHTML = `<div class="card"><div class="alert alert-error">Error: ${error.message}</div></div>`;
  }
});
