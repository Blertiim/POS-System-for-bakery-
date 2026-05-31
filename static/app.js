const PIN_ROLES = {
  1: "cashier",
  2: "admin",
};

const ROLE_LABELS = {
  cashier: "Arkëtar",
  admin: "Admin",
};

const state = {
  role: null,
  categories: [],
  products: [],
  currentCategoryId: null,
  order: new Map(),
  selectedLineId: null,
  adminTab: "products",
};

const els = {};

document.addEventListener("DOMContentLoaded", () => {
  cacheElements();
  bindEvents();
  tickClock();
  setInterval(tickClock, 1000);
  setDefaultReportDate();
});

function cacheElements() {
  [
    "toast",
    "login-screen",
    "pin-input",
    "login-submit",
    "login-message",
    "cashier-screen",
    "cashier-clock",
    "cashier-logout",
    "order-total-top",
    "order-lines",
    "increase-qty",
    "decrease-qty",
    "delete-line",
    "clear-order",
    "open-calculator",
    "payment-box",
    "payment-total",
    "amount-received",
    "payment-keypad",
    "change-due",
    "payment-message",
    "pay-button",
    "product-search",
    "category-tabs",
    "product-grid",
    "admin-screen",
    "admin-clock",
    "admin-logout",
    "admin-products-panel",
    "admin-categories-panel",
    "admin-sales-panel",
    "product-form",
    "product-id",
    "product-name",
    "product-category",
    "product-price",
    "product-active",
    "reset-product-form",
    "admin-product-search",
    "admin-products",
    "category-form",
    "category-id",
    "category-name",
    "category-active",
    "reset-category-form",
    "admin-categories",
    "report-date",
    "report-sale-count",
    "report-revenue",
    "sales-history",
    "receipt-modal",
    "receipt-title",
    "receipt-text",
    "close-receipt",
    "print-receipt",
    "download-receipt",
  ].forEach((id) => {
    els[toCamel(id)] = document.getElementById(id);
  });
}

function bindEvents() {
  document.querySelectorAll("[data-pin]").forEach((button) => {
    button.addEventListener("click", () => {
      if (els.pinInput.value.length < 4) {
        els.pinInput.value += button.dataset.pin;
      }
    });
  });

  document.querySelectorAll("[data-pin-action]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.pinAction === "clear") {
        els.pinInput.value = "";
      } else {
        els.pinInput.value = els.pinInput.value.slice(0, -1);
      }
    });
  });

  els.loginSubmit.addEventListener("click", login);
  document.addEventListener("keydown", (event) => {
    if (!els.loginScreen.classList.contains("hidden") && event.key === "Enter") {
      login();
    }
  });

  els.cashierLogout.addEventListener("click", logout);
  els.adminLogout.addEventListener("click", logout);

  els.categoryTabs.addEventListener("click", (event) => {
    const button = event.target.closest("[data-category-id]");
    if (!button) return;
    state.currentCategoryId = Number(button.dataset.categoryId);
    renderCategories();
    renderProducts();
  });

  els.productGrid.addEventListener("click", (event) => {
    const button = event.target.closest("[data-product-id]");
    if (!button) return;
    const product = state.products.find((item) => item.id === Number(button.dataset.productId));
    if (product) addToOrder(product);
  });

  els.productSearch.addEventListener("input", renderProducts);
  els.amountReceived.addEventListener("input", renderPayment);
  els.paymentKeypad.addEventListener("click", handleCalculatorKey);

  els.orderLines.addEventListener("click", (event) => {
    const row = event.target.closest("[data-line-id]");
    if (!row) return;
    state.selectedLineId = row.dataset.lineId;
    renderOrder();
  });

  els.increaseQty.addEventListener("click", () => changeSelectedQuantity(1));
  els.decreaseQty.addEventListener("click", () => changeSelectedQuantity(-1));
  els.deleteLine.addEventListener("click", deleteSelectedLine);
  els.clearOrder.addEventListener("click", clearOrder);
  els.openCalculator.addEventListener("click", toggleCalculator);
  els.payButton.addEventListener("click", completeSale);

  document.querySelectorAll("[data-admin-tab]").forEach((button) => {
    button.addEventListener("click", () => setAdminTab(button.dataset.adminTab));
  });

  els.productForm.addEventListener("submit", saveProduct);
  els.resetProductForm.addEventListener("click", resetProductForm);
  els.adminProductSearch.addEventListener("input", renderAdminProducts);

  els.adminProducts.addEventListener("click", (event) => {
    const editButton = event.target.closest("[data-edit-product]");
    const deleteButton = event.target.closest("[data-delete-product]");
    if (editButton) editProduct(Number(editButton.dataset.editProduct));
    if (deleteButton) removeProduct(Number(deleteButton.dataset.deleteProduct));
  });

  els.categoryForm.addEventListener("submit", saveCategory);
  els.resetCategoryForm.addEventListener("click", resetCategoryForm);
  els.adminCategories.addEventListener("click", (event) => {
    const editButton = event.target.closest("[data-edit-category]");
    const deleteButton = event.target.closest("[data-delete-category]");
    if (editButton) editCategory(Number(editButton.dataset.editCategory));
    if (deleteButton) removeCategory(Number(deleteButton.dataset.deleteCategory));
  });

  els.reportDate.addEventListener("change", loadReport);
  els.salesHistory.addEventListener("click", (event) => {
    const receiptButton = event.target.closest("[data-sale-receipt]");
    if (receiptButton) showReceipt(Number(receiptButton.dataset.saleReceipt));
  });

  els.closeReceipt.addEventListener("click", closeReceipt);
  els.receiptModal.addEventListener("click", (event) => {
    if (event.target === els.receiptModal) closeReceipt();
  });
  els.printReceipt.addEventListener("click", () => window.print());
}

function toCamel(id) {
  return id.replace(/-([a-z])/g, (_, char) => char.toUpperCase());
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!response.ok) {
    let message = "Ndodhi një gabim.";
    try {
      const payload = await response.json();
      message = payload.error || message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }
  return response.json();
}

function login() {
  const pin = els.pinInput.value.trim();
  const role = PIN_ROLES[pin];
  if (!role) {
    els.loginMessage.textContent = "PIN i pasaktë.";
    els.loginMessage.classList.add("error");
    els.pinInput.value = "";
    return;
  }

  state.role = role;
  els.loginMessage.classList.remove("error");
  els.pinInput.value = "";
  if (role === "cashier") {
    openCashier();
  } else {
    openAdmin();
  }
}

function logout() {
  state.role = null;
  clearOrder();
  showScreen("login");
}

function showScreen(screen) {
  els.loginScreen.classList.toggle("hidden", screen !== "login");
  els.cashierScreen.classList.toggle("hidden", screen !== "cashier");
  els.adminScreen.classList.toggle("hidden", screen !== "admin");
}

async function openCashier() {
  showScreen("cashier");
  try {
    await loadCatalog(false);
    state.currentCategoryId = state.categories[0]?.id || null;
    renderCategories();
    renderProducts();
    renderOrder();
    renderPayment();
  } catch (error) {
    showToast(error.message);
  }
}

async function openAdmin() {
  showScreen("admin");
  try {
    await loadAdminData();
    setAdminTab("products");
  } catch (error) {
    showToast(error.message);
  }
}

async function loadCatalog(includeInactive) {
  const suffix = includeInactive ? "?include_inactive=1" : "";
  const [categories, products] = await Promise.all([
    api(`/api/categories${suffix}`),
    api(`/api/products${suffix}`),
  ]);
  state.categories = categories;
  state.products = products;
}

function renderCategories() {
  const activeCategories = state.categories.filter((category) => category.active);
  if (!state.currentCategoryId && activeCategories.length) {
    state.currentCategoryId = activeCategories[0].id;
  }
  els.categoryTabs.innerHTML = activeCategories
    .map(
      (category) => `
        <button
          type="button"
          class="${category.id === state.currentCategoryId ? "active" : ""}"
          data-category-id="${category.id}">
          ${escapeHtml(category.name)}
        </button>
      `,
    )
    .join("");
}

function renderProducts() {
  const search = els.productSearch.value.trim().toLowerCase();
  const filtered = state.products.filter((product) => {
    const matchesCategory = search ? true : product.category_id === state.currentCategoryId;
    const matchesSearch = product.name.toLowerCase().includes(search);
    return product.active && matchesCategory && matchesSearch;
  });

  if (!filtered.length) {
    els.productGrid.innerHTML = `<div class="empty-state">Nuk u gjet asnjë produkt.</div>`;
    return;
  }

  els.productGrid.innerHTML = filtered
    .map(
      (product) => `
        <button type="button" class="product-button" data-product-id="${product.id}">
          <strong>${escapeHtml(product.name)}</strong>
          <span>${formatCents(product.price_cents)}</span>
        </button>
      `,
    )
    .join("");
}

function addToOrder(product) {
  const key = String(product.id);
  const current = state.order.get(key);
  if (current) {
    current.quantity += 1;
  } else {
    state.order.set(key, { product, quantity: 1 });
  }
  state.selectedLineId = key;
  renderOrder();
  renderPayment();
}

function renderOrder() {
  const lines = Array.from(state.order.entries());
  if (!lines.length) {
    els.orderLines.innerHTML = `
      <tr>
        <td colspan="4" class="empty-state">Shtoni produkte nga paneli djathtas.</td>
      </tr>
    `;
    state.selectedLineId = null;
    updateOrderTotals();
    return;
  }

  if (!state.selectedLineId || !state.order.has(state.selectedLineId)) {
    state.selectedLineId = lines[0][0];
  }

  els.orderLines.innerHTML = lines
    .map(([id, line]) => {
      const lineTotal = line.quantity * line.product.price_cents;
      return `
        <tr class="selectable ${id === state.selectedLineId ? "selected" : ""}" data-line-id="${id}">
          <td>${escapeHtml(line.product.name)}</td>
          <td>${line.quantity}</td>
          <td>${formatCents(line.product.price_cents)}</td>
          <td>${formatCents(lineTotal)}</td>
        </tr>
      `;
    })
    .join("");

  updateOrderTotals();
}

function updateOrderTotals() {
  const total = calculateOrderTotalCents();
  els.orderTotalTop.textContent = formatCents(total);
  els.paymentTotal.textContent = formatCents(total);
}

function changeSelectedQuantity(delta) {
  const selected = state.order.get(state.selectedLineId);
  if (!selected) {
    showToast("Zgjidhni një artikull.");
    return;
  }
  selected.quantity += delta;
  if (selected.quantity <= 0) {
    state.order.delete(state.selectedLineId);
    state.selectedLineId = null;
  }
  renderOrder();
  renderPayment();
}

function deleteSelectedLine() {
  if (!state.selectedLineId || !state.order.has(state.selectedLineId)) {
    showToast("Zgjidhni një artikull për ta fshirë.");
    return;
  }
  state.order.delete(state.selectedLineId);
  state.selectedLineId = null;
  renderOrder();
  renderPayment();
}

function clearOrder() {
  state.order.clear();
  state.selectedLineId = null;
  if (els.amountReceived) els.amountReceived.value = "";
  if (els.paymentBox) els.paymentBox.classList.add("hidden");
  if (els.openCalculator) els.openCalculator.classList.remove("active");
  if (els.orderLines) renderOrder();
  if (els.paymentMessage) renderPayment();
}

function calculateOrderTotalCents() {
  return Array.from(state.order.values()).reduce(
    (sum, line) => sum + line.product.price_cents * line.quantity,
    0,
  );
}

function renderPayment() {
  const total = calculateOrderTotalCents();
  const paid = parseMoneyInput(els.amountReceived.value);
  const change = paid - total;
  els.paymentTotal.textContent = formatCents(total);
  els.changeDue.textContent = formatCents(Math.max(change, 0));
  els.paymentMessage.classList.remove("error");
  els.paymentMessage.textContent = "";

  if (total > 0 && els.amountReceived.value && paid < total) {
    els.paymentMessage.textContent = "Insufficient amount received.";
    els.paymentMessage.classList.add("error");
  }
}

function handleCalculatorKey(event) {
  const button = event.target.closest("[data-calc-key]");
  if (!button) return;

  const key = button.dataset.calcKey;
  if (key === "clear") {
    els.amountReceived.value = "";
  } else if (key === "back") {
    els.amountReceived.value = els.amountReceived.value.slice(0, -1);
  } else if (key === "exact") {
    els.amountReceived.value = centsToInput(calculateOrderTotalCents());
  } else {
    els.amountReceived.value = appendPaymentKey(els.amountReceived.value, key);
  }

  renderPayment();
}

function appendPaymentKey(currentValue, key) {
  let value = String(currentValue || "").replace(",", ".");

  if (key === ".") {
    return value.includes(".") ? value : `${value || "0"}.`;
  }

  if (!/^\d+$/.test(key)) {
    return value;
  }

  const candidate = `${value}${key}`;
  const parts = candidate.split(".");
  if (parts.length > 2 || (parts[1] && parts[1].length > 2)) {
    return value;
  }

  const euros = (parts[0] || "0").replace(/^0+(?=\d)/, "") || "0";
  return parts.length === 2 ? `${euros}.${parts[1]}` : euros;
}

function centsToInput(cents) {
  return ((Number(cents) || 0) / 100).toFixed(2);
}

function toggleCalculator() {
  const opening = els.paymentBox.classList.contains("hidden");
  els.paymentBox.classList.toggle("hidden", !opening);
  els.openCalculator.classList.toggle("active", opening);
  if (opening) {
    renderPayment();
  }
}

async function completeSale() {
  const total = calculateOrderTotalCents();
  const calculatorOpen = !els.paymentBox.classList.contains("hidden");
  const amountTyped = els.amountReceived.value.trim() !== "";
  const paid = calculatorOpen && amountTyped ? parseMoneyInput(els.amountReceived.value) : total;
  if (total <= 0) {
    showToast("Porosia është bosh.");
    return;
  }
  if (calculatorOpen && amountTyped && paid < total) {
    els.paymentMessage.textContent = "Insufficient amount received.";
    els.paymentMessage.classList.add("error");
    return;
  }

  const payload = {
    cashier_role: ROLE_LABELS[state.role] || "Arkëtar",
    amount_received: (paid / 100).toFixed(2),
    items: Array.from(state.order.values()).map((line) => ({
      product_id: line.product.id,
      quantity: line.quantity,
    })),
  };

  try {
    await api("/api/sales", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    clearOrder();
    showToast("Shitja u përfundua me sukses.");
  } catch (error) {
    els.paymentMessage.textContent = error.message;
    els.paymentMessage.classList.add("error");
  }
}

async function showReceipt(saleId) {
  const [sale, receiptResponse] = await Promise.all([
    api(`/api/sales/${saleId}`),
    fetch(`/api/receipts/${saleId}.txt`),
  ]);
  const text = await receiptResponse.text();
  els.receiptTitle.textContent = `Kuponi ${sale.receipt_no}`;
  els.receiptText.textContent = text;
  els.downloadReceipt.href = `/api/receipts/${saleId}.txt`;
  els.downloadReceipt.download = `${sale.receipt_no}.txt`;
  els.receiptModal.classList.remove("hidden");
}

function closeReceipt() {
  els.receiptModal.classList.add("hidden");
}

async function loadAdminData() {
  await loadCatalog(false);
  renderProductSelect();
  renderAdminProducts();
  renderAdminCategories();
  await loadReport();
}

function setAdminTab(tab) {
  state.adminTab = tab;
  document.querySelectorAll("[data-admin-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.adminTab === tab);
  });
  els.adminProductsPanel.classList.toggle("hidden", tab !== "products");
  els.adminCategoriesPanel.classList.toggle("hidden", tab !== "categories");
  els.adminSalesPanel.classList.toggle("hidden", tab !== "sales");
  if (tab === "sales") loadReport();
}

function renderProductSelect() {
  els.productCategory.innerHTML = state.categories
    .map(
      (category) => `
        <option value="${category.id}">
          ${escapeHtml(category.name)}
        </option>
      `,
    )
    .join("");
}

function renderAdminProducts() {
  const search = els.adminProductSearch.value.trim().toLowerCase();
  const products = state.products.filter((product) =>
    product.name.toLowerCase().includes(search),
  );

  if (!products.length) {
    els.adminProducts.innerHTML = `
      <tr><td colspan="5" class="empty-state">Nuk ka produkte.</td></tr>
    `;
    return;
  }

  els.adminProducts.innerHTML = products
    .map(
      (product) => `
        <tr>
          <td>${escapeHtml(product.name)}</td>
          <td>${escapeHtml(product.category_name)}</td>
          <td>${formatCents(product.price_cents)}</td>
          <td>
            <span class="status-pill ${product.active ? "" : "inactive"}">
              ${product.active ? "Aktiv" : "Joaktiv"}
            </span>
          </td>
          <td>
            <button type="button" class="row-action" data-edit-product="${product.id}">Edit</button>
            <button type="button" class="row-action danger" data-delete-product="${product.id}">Fshi</button>
          </td>
        </tr>
      `,
    )
    .join("");
}

async function saveProduct(event) {
  event.preventDefault();
  const id = els.productId.value;
  const payload = {
    name: els.productName.value.trim(),
    category_id: Number(els.productCategory.value),
    price: els.productPrice.value,
    active: els.productActive.checked,
  };
  try {
    await api(id ? `/api/products/${id}` : "/api/products", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
    showToast("Produkti u ruajt.");
    resetProductForm();
    await loadAdminData();
  } catch (error) {
    showToast(error.message);
  }
}

function editProduct(productId) {
  const product = state.products.find((item) => item.id === productId);
  if (!product) return;
  els.productId.value = product.id;
  els.productName.value = product.name;
  els.productCategory.value = product.category_id;
  els.productPrice.value = (product.price_cents / 100).toFixed(2);
  els.productActive.checked = product.active;
  els.productName.focus();
}

async function removeProduct(productId) {
  if (!window.confirm("A dëshironi ta fshini këtë produkt?")) return;
  try {
    await api(`/api/products/${productId}`, { method: "DELETE" });
    showToast("Produkti u fshi nga shitja aktive.");
    await loadAdminData();
  } catch (error) {
    showToast(error.message);
  }
}

function resetProductForm() {
  els.productForm.reset();
  els.productId.value = "";
  els.productActive.checked = true;
}

function renderAdminCategories() {
  if (!state.categories.length) {
    els.adminCategories.innerHTML = `
      <tr><td colspan="3" class="empty-state">Nuk ka kategori.</td></tr>
    `;
    return;
  }

  els.adminCategories.innerHTML = state.categories
    .map(
      (category) => `
        <tr>
          <td>${escapeHtml(category.name)}</td>
          <td>
            <span class="status-pill ${category.active ? "" : "inactive"}">
              ${category.active ? "Aktive" : "Joaktive"}
            </span>
          </td>
          <td>
            <button type="button" class="row-action" data-edit-category="${category.id}">Edit</button>
            <button type="button" class="row-action danger" data-delete-category="${category.id}">Fshi</button>
          </td>
        </tr>
      `,
    )
    .join("");
}

async function saveCategory(event) {
  event.preventDefault();
  const id = els.categoryId.value;
  const payload = {
    name: els.categoryName.value.trim(),
    active: els.categoryActive.checked,
  };
  try {
    await api(id ? `/api/categories/${id}` : "/api/categories", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
    showToast("Kategoria u ruajt.");
    resetCategoryForm();
    await loadAdminData();
  } catch (error) {
    showToast(error.message);
  }
}

function editCategory(categoryId) {
  const category = state.categories.find((item) => item.id === categoryId);
  if (!category) return;
  els.categoryId.value = category.id;
  els.categoryName.value = category.name;
  els.categoryActive.checked = category.active;
  els.categoryName.focus();
}

async function removeCategory(categoryId) {
  if (!window.confirm("A dëshironi ta fshini këtë kategori?")) return;
  try {
    await api(`/api/categories/${categoryId}`, { method: "DELETE" });
    showToast("Kategoria u fshi.");
    await loadAdminData();
  } catch (error) {
    showToast(error.message);
  }
}

function resetCategoryForm() {
  els.categoryForm.reset();
  els.categoryId.value = "";
  els.categoryActive.checked = true;
}

async function loadReport() {
  if (!els.reportDate.value) setDefaultReportDate();
  const date = els.reportDate.value;
  try {
    const [report, sales] = await Promise.all([
      api(`/api/reports/daily?date=${encodeURIComponent(date)}`),
      api(`/api/sales?date=${encodeURIComponent(date)}`),
    ]);
    renderReport(report, sales);
  } catch (error) {
    showToast(error.message);
  }
}

function renderReport(report, sales) {
  els.reportSaleCount.textContent = report.sale_count;
  els.reportRevenue.textContent = formatCents(report.revenue_cents);

  if (!sales.length) {
    els.salesHistory.innerHTML = `
      <tr><td colspan="5" class="empty-state">Nuk ka shitje për këtë datë.</td></tr>
    `;
  } else {
    els.salesHistory.innerHTML = sales
      .map(
        (sale) => `
          <tr>
            <td>${escapeHtml(sale.receipt_no)}</td>
            <td>${formatDateTime(sale.created_at, "time")}</td>
            <td>${sale.item_count}</td>
            <td>${formatCents(sale.total_cents)}</td>
            <td>
              <button type="button" class="row-action" data-sale-receipt="${sale.id}">Kuponi</button>
            </td>
          </tr>
        `,
      )
      .join("");
  }
}

function setDefaultReportDate() {
  if (!els.reportDate) return;
  els.reportDate.value = localDateInputValue(new Date());
}

function tickClock() {
  const value = new Intl.DateTimeFormat("sq-AL", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date());
  if (els.cashierClock) els.cashierClock.textContent = value;
  if (els.adminClock) els.adminClock.textContent = value;
}

function parseMoneyInput(value) {
  if (!value) return 0;
  const number = Number(String(value).replace(",", "."));
  if (!Number.isFinite(number) || number < 0) return 0;
  return Math.round(number * 100);
}

function formatCents(cents) {
  return new Intl.NumberFormat("sq-AL", {
    style: "currency",
    currency: "EUR",
  }).format((Number(cents) || 0) / 100);
}

function formatDateTime(value, mode = "full") {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const options = mode === "time" ? { timeStyle: "short" } : { dateStyle: "short", timeStyle: "short" };
  return new Intl.DateTimeFormat("sq-AL", options).format(date);
}

function localDateInputValue(date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

let toastTimer = null;
function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    els.toast.classList.remove("show");
  }, 2600);
}
