import { loadPublicConfig } from "./runtime-config.mjs";
import { Sidebar, DashboardHeader } from "./components.js";
import { track } from "./src/services/telemetry.mjs";

const app = document.querySelector("#app");
const runtimeConfig = await loadPublicConfig();
const apiBase = runtimeConfig.NEXT_PUBLIC_ADMIN_API_ENDPOINT || window.BRASALAND_API_URL || "http://127.0.0.1:8000";

// Valid categories from BRIEFING
const VALID_CATEGORIES = [
  { value: "carne", label: "Carne" },
  { value: "verduras_y_hortalizas", label: "Verduras y Hortalizas" },
  { value: "salsas_y_condimentos", label: "Salsas y Condimentos" },
  { value: "bebidas", label: "Bebidas" },
  { value: "packaging", label: "Packaging" },
  { value: "productos_limpieza", label: "Productos de Limpieza" },
  { value: "lacteos", label: "Lácteos" },
  { value: "carbon_y_combustible", label: "Carbón y Combustible" }
];

const COUNTRIES = [
  { value: "Colombia", label: "Colombia", currency: "COP" },
  { value: "USA", label: "USA", currency: "USD" }
];

// State
let suppliers = [];
let filteredSuppliers = [];
let currentFilter = { country: null, category: null };
let editingSupplier = null;

// Initialize app
async function init() {
  renderUI();
  await loadSuppliers();
  setupEventListeners();
  track("section_viewed", { section_id: "suppliers", client_area: "backoffice", navigation_source: "menu" });
}

function renderUI() {
  app.innerHTML = `
    <div class="layout">
      ${Sidebar()}
      <main class="content">
        <div class="suppliers-container">
          <div class="suppliers-header">
            <h1>📦 Directorio de Proveedores</h1>
            <button class="add-supplier-btn" id="add-supplier-btn">+ Agregar Proveedor</button>
          </div>

          <div id="alert-container"></div>

          <div class="filters">
            <div class="filter-group">
              <label for="country-filter">País</label>
              <select id="country-filter">
                <option value="">Todos los países</option>
                ${COUNTRIES.map(c => `<option value="${c.value}">${c.label}</option>`).join("")}
              </select>
            </div>
            <div class="filter-group">
              <label for="category-filter">Categoría</label>
              <select id="category-filter">
                <option value="">Todas las categorías</option>
                ${VALID_CATEGORIES.map(c => `<option value="${c.value}">${c.label}</option>`).join("")}
              </select>
            </div>
          </div>

          <div id="suppliers-list"></div>
        </div>
      </main>
    </div>

    <!-- Modal de Proveedor -->
    <div id="supplier-modal" class="modal">
      <div class="modal-content">
        <div class="modal-header">
          <h2 id="modal-title">Agregar Proveedor</h2>
          <button class="close-btn" id="close-modal-btn">&times;</button>
        </div>
        <form id="supplier-form">
          <div id="form-alert"></div>

          <div class="form-group">
            <label for="supplier-name">Nombre *</label>
            <input type="text" id="supplier-name" required />
          </div>

          <div class="form-group">
            <label for="supplier-country">País *</label>
            <select id="supplier-country" required>
              <option value="">Selecciona un país</option>
              ${COUNTRIES.map(c => `<option value="${c.value}">${c.label}</option>`).join("")}
            </select>
          </div>

          <div class="form-group">
            <label>Categorías *</label>
            <div class="categories-checkboxes">
              ${VALID_CATEGORIES.map(c => `
                <div class="checkbox-item">
                  <input type="checkbox" id="cat-${c.value}" value="${c.value}" name="category" />
                  <label for="cat-${c.value}">${c.label}</label>
                </div>
              `).join("")}
            </div>
          </div>

          <div class="form-group">
            <label for="supplier-rate">Tarifa por Unidad *</label>
            <input type="number" id="supplier-rate" step="0.01" min="0.01" required />
          </div>

          <div class="form-group">
            <label for="supplier-currency">Moneda *</label>
            <select id="supplier-currency" required disabled>
              <option value="">Selecciona país primero</option>
            </select>
          </div>

          <div class="form-group">
            <label for="supplier-status">Estado *</label>
            <select id="supplier-status" required>
              <option value="active">Activo</option>
              <option value="suspended">Suspendido</option>
            </select>
          </div>

          <div class="form-group">
            <label for="supplier-email">Email de Contacto</label>
            <input type="email" id="supplier-email" />
          </div>

          <div class="form-group">
            <label for="supplier-notes">Notas</label>
            <textarea id="supplier-notes"></textarea>
          </div>

          <div class="form-actions">
            <button type="button" class="btn-secondary" id="cancel-btn">Cancelar</button>
            <button type="submit" class="btn-primary">Guardar Proveedor</button>
          </div>
        </form>
      </div>
    </div>
  `;
}

function setupEventListeners() {
  // Modal controls
  document.getElementById("add-supplier-btn").addEventListener("click", openAddModal);
  document.getElementById("close-modal-btn").addEventListener("click", closeModal);
  document.getElementById("cancel-btn").addEventListener("click", closeModal);
  document.getElementById("supplier-form").addEventListener("submit", handleFormSubmit);

  // Filter controls
  document.getElementById("country-filter").addEventListener("change", applyFilters);
  document.getElementById("category-filter").addEventListener("change", applyFilters);

  // Country change updates currency
  document.getElementById("supplier-country").addEventListener("change", updateCurrency);

  // Close modal when clicking outside
  document.getElementById("supplier-modal").addEventListener("click", (e) => {
    if (e.target.id === "supplier-modal") closeModal();
  });
}

function updateCurrency() {
  const country = document.getElementById("supplier-country").value;
  const currencySelect = document.getElementById("supplier-currency");

  if (country) {
    const selectedCountry = COUNTRIES.find(c => c.value === country);
    currencySelect.innerHTML = `<option value="${selectedCountry.currency}">${selectedCountry.currency}</option>`;
    currencySelect.disabled = false;
    currencySelect.value = selectedCountry.currency;
  } else {
    currencySelect.innerHTML = '<option value="">Selecciona país primero</option>';
    currencySelect.disabled = true;
  }
}

async function loadSuppliers() {
  try {
    const response = await fetch(`${apiBase}/suppliers`);
    if (!response.ok) throw new Error("Failed to load suppliers");
    suppliers = await response.json();
    filteredSuppliers = [...suppliers];
    renderSuppliers();
  } catch (error) {
    showAlert("Error al cargar proveedores", "error");
    console.error(error);
  }
}

function applyFilters() {
  const country = document.getElementById("country-filter").value;
  const category = document.getElementById("category-filter").value;

  filteredSuppliers = suppliers.filter(supplier => {
    if (country && supplier.country !== country) return false;
    if (category && !supplier.categories.includes(category)) return false;
    return true;
  });

  renderSuppliers();
}

function renderSuppliers() {
  const container = document.getElementById("suppliers-list");

  if (filteredSuppliers.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <h3>No hay proveedores</h3>
        <p>Agrega un nuevo proveedor para comenzar</p>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <table class="suppliers-table">
      <thead>
        <tr>
          <th>Nombre</th>
          <th>País</th>
          <th>Categorías</th>
          <th>Tarifa</th>
          <th>Estado</th>
          <th>Acciones</th>
        </tr>
      </thead>
      <tbody>
        ${filteredSuppliers.map(supplier => `
          <tr>
            <td><strong>${supplier.name}</strong><br><small>${supplier.contact_email || "-"}</small></td>
            <td>${supplier.country}</td>
            <td>
              <div class="categories-list">
                ${supplier.categories.map(cat => {
                  const label = VALID_CATEGORIES.find(c => c.value === cat)?.label || cat;
                  return `<span class="category-tag">${label}</span>`;
                }).join("")}
              </div>
            </td>
            <td>
              <div>${supplier.rate_per_unit.toFixed(2)} ${supplier.currency}</div>
              <div class="rate-update-section">
                <small style="color: #999;">Actualizado: ${new Date(supplier.updated_at).toLocaleString('es-ES')}</small>
              </div>
            </td>
            <td>
              <span class="status-badge ${supplier.status === 'active' ? 'status-active' : 'status-suspended'}">
                ${supplier.status === 'active' ? '✓ Activo' : '⊗ Suspendido'}
              </span>
            </td>
            <td>
              <div class="action-buttons">
                <button class="btn-sm btn-edit" onclick="editSupplier(${supplier.id})">Editar</button>
                <button class="btn-sm ${supplier.status === 'active' ? 'btn-suspend' : 'btn-edit'}" onclick="toggleStatus(${supplier.id}, '${supplier.status === 'active' ? 'suspended' : 'active'}')">
                  ${supplier.status === 'active' ? 'Suspender' : 'Activar'}
                </button>
                <button class="btn-sm btn-delete" onclick="deleteSupplier(${supplier.id})">Eliminar</button>
              </div>
            </td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function openAddModal() {
  editingSupplier = null;
  document.getElementById("modal-title").textContent = "Agregar Proveedor";
  document.getElementById("supplier-form").reset();
  document.getElementById("supplier-country").value = "";
  document.getElementById("supplier-currency").disabled = true;
  document.getElementById("supplier-status").value = "active";
  document.getElementById("form-alert").innerHTML = "";
  document.getElementById("supplier-modal").classList.add("active");
}

function closeModal() {
  document.getElementById("supplier-modal").classList.remove("active");
  editingSupplier = null;
}

async function handleFormSubmit(e) {
  e.preventDefault();

  const formAlert = document.getElementById("form-alert");
  formAlert.innerHTML = "";

  const name = document.getElementById("supplier-name").value;
  const country = document.getElementById("supplier-country").value;
  const categories = Array.from(document.querySelectorAll('input[name="category"]:checked')).map(el => el.value);
  const rate = parseFloat(document.getElementById("supplier-rate").value);
  const currency = document.getElementById("supplier-currency").value;
  const status = document.getElementById("supplier-status").value;
  const email = document.getElementById("supplier-email").value || null;
  const notes = document.getElementById("supplier-notes").value || null;

  if (categories.length === 0) {
    showAlertInModal("Selecciona al menos una categoría", "error");
    return;
  }

  const data = {
    name,
    country,
    categories,
    rate_per_unit: rate,
    currency,
    status,
    contact_email: email,
    notes
  };

  try {
    const response = await fetch(`${apiBase}/suppliers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      const error = await response.json();
      showAlertInModal(`Error: ${error.detail || "No se pudo guardar el proveedor"}`, "error");
      return;
    }

    showAlert("Proveedor guardado exitosamente", "success");
    closeModal();
    await loadSuppliers();
  } catch (error) {
    showAlertInModal("Error de conexión", "error");
    console.error(error);
  }
}

window.editSupplier = async function(id) {
  const supplier = suppliers.find(s => s.id === id);
  if (!supplier) return;

  editingSupplier = supplier;
  document.getElementById("modal-title").textContent = "Editar Proveedor";
  document.getElementById("supplier-name").value = supplier.name;
  document.getElementById("supplier-country").value = supplier.country;
  document.getElementById("supplier-rate").value = supplier.rate_per_unit;
  document.getElementById("supplier-status").value = supplier.status;
  document.getElementById("supplier-email").value = supplier.contact_email || "";
  document.getElementById("supplier-notes").value = supplier.notes || "";

  // Update currency select
  const currencySelect = document.getElementById("supplier-currency");
  currencySelect.innerHTML = `<option value="${supplier.currency}">${supplier.currency}</option>`;
  currencySelect.value = supplier.currency;

  // Check categories
  document.querySelectorAll('input[name="category"]').forEach(cb => {
    cb.checked = supplier.categories.includes(cb.value);
  });

  document.getElementById("supplier-modal").classList.add("active");
};

window.toggleStatus = async function(id, newStatus) {
  if (!confirm(`¿Estás seguro de que deseas ${newStatus === 'active' ? 'activar' : 'suspender'} este proveedor?`)) {
    return;
  }

  try {
    const response = await fetch(`${apiBase}/suppliers/${id}/status?status_value=${newStatus}`, {
      method: "PATCH"
    });

    if (!response.ok) throw new Error("Failed to update status");

    showAlert("Estado actualizado", "success");
    await loadSuppliers();
  } catch (error) {
    showAlert("Error al actualizar estado", "error");
    console.error(error);
  }
};

window.deleteSupplier = async function(id) {
  if (!confirm("¿Estás seguro de que deseas eliminar este proveedor?")) {
    return;
  }

  try {
    const response = await fetch(`${apiBase}/suppliers/${id}`, {
      method: "DELETE"
    });

    if (!response.ok) throw new Error("Failed to delete supplier");

    showAlert("Proveedor eliminado", "success");
    await loadSuppliers();
  } catch (error) {
    showAlert("Error al eliminar proveedor", "error");
    console.error(error);
  }
};

function showAlert(message, type) {
  const container = document.getElementById("alert-container");
  const alertClass = type === "success" ? "alert-success" : "alert-error";
  container.innerHTML = `<div class="alert ${alertClass}">${message}</div>`;
  setTimeout(() => {
    container.innerHTML = "";
  }, 5000);
}

function showAlertInModal(message, type) {
  const container = document.getElementById("form-alert");
  const alertClass = type === "success" ? "alert-success" : "alert-error";
  container.innerHTML = `<div class="alert ${alertClass}">${message}</div>`;
}

// Initialize
init();
