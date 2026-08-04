"use strict";

const byId = (id) => document.getElementById(id);
const state = {
  cities: [],
  key: "",
  geocodingAuditId: "",
  geocodingEvidence: "",
  geocodingAddressSignature: "",
};

function setResult(id, message, kind = "info") {
  const element = byId(id);
  element.textContent = message;
  element.className = `result result-${kind}`;
}

function clearResult(id) {
  const element = byId(id);
  element.textContent = "";
  element.className = "result";
}

function clientHeaders(json = false) {
  const headers = {};
  const key = byId("client-key").value.trim();
  state.key = key;
  if (key) headers["X-Client-API-Key"] = key;
  if (json) headers["Content-Type"] = "application/json";
  return headers;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { ...clientHeaders(Boolean(options.body)), ...(options.headers || {}) },
  });
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      const detail = body.detail || body;
      message = `${detail.code || message}: ${detail.message || "Requisição recusada."}`;
    } catch (_) {
      // A resposta pode não possuir corpo JSON.
    }
    throw new Error(message);
  }
  return response;
}

async function checkHealth() {
  const badge = byId("health-badge");
  try {
    const response = await fetch("/health/ready");
    const body = await response.json();
    if (!response.ok || body.status !== "ok" || body.database !== "ok") throw new Error();
    badge.textContent = `${body.environment} · ${body.execution_mode} · API e banco disponíveis`;
    badge.className = "health health-ok";
  } catch (_) {
    badge.textContent = "Ambiente indisponível";
    badge.className = "health health-error";
  }
}

async function loadCities() {
  const select = byId("city");
  try {
    const response = await fetch("/cities");
    state.cities = await response.json();
    select.replaceChildren();
    for (const city of state.cities) {
      const option = document.createElement("option");
      option.value = city.city_ibge_code;
      option.textContent = `${city.name}/${city.state} · IBGE ${city.city_ibge_code}`;
      option.dataset.name = city.name;
      option.dataset.state = city.state;
      select.append(option);
    }
  } catch (_) {
    select.innerHTML = '<option value="">Não foi possível carregar as cidades</option>';
  }
}

function nullableNumber(id) {
  const value = byId(id).value;
  return value === "" ? null : Number(value);
}

function addressPayload() {
  const cityOption = byId("city").selectedOptions[0];
  if (!cityOption || !cityOption.value) throw new Error("Selecione a cidade.");
  const payload = {
    city_ibge_code: cityOption.value,
    state: cityOption.dataset.state,
    city: cityOption.dataset.name,
    postal_code: byId("postal-code").value.trim(),
    street: byId("street").value.trim(),
    number: byId("number").value.trim(),
    complement: byId("complement").value.trim() || null,
  };
  for (const field of ["postal_code", "street", "number"]) {
    if (!payload[field]) throw new Error("Preencha CEP, logradouro e número antes da busca.");
  }
  return payload;
}

function addressSignature() {
  return JSON.stringify(addressPayload());
}

function resetAutomaticGeocoding() {
  state.geocodingAuditId = "";
  state.geocodingEvidence = "";
  state.geocodingAddressSignature = "";
  byId("latitude").value = "";
  byId("longitude").value = "";
  byId("accuracy").value = "";
  byId("confirmation-method").value = "DOCUMENT_VALIDATION";
  byId("verified-by").value = "";
  clearResult("geocoding-result");
}

async function resolveAddress() {
  clearResult("geocoding-result");
  try {
    const payload = addressPayload();
    const response = await api("/geocoding/resolve", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!result.automatic_coordinates_allowed || !result.selected) {
      resetAutomaticGeocoding();
      setResult("geocoding-result", `${result.status}: ${result.message} Auditoria ${result.audit_id}.`, "error");
      return;
    }
    byId("latitude").value = result.selected.latitude;
    byId("longitude").value = result.selected.longitude;
    byId("accuracy").value = "";
    byId("confirmation-method").value = "CNEFE_IBGE";
    byId("verified-by").value = "";
    state.geocodingAuditId = result.audit_id;
    state.geocodingEvidence = result.evidence_reference;
    state.geocodingAddressSignature = JSON.stringify(payload);
    const quality = `nível ${result.selected.geocoding_level} (${result.selected.geocoding_level_description})`;
    setResult(
      "geocoding-result",
      `Coordenadas sugeridas. Qualidade CNEFE: ${quality}. Auditoria ${result.audit_id}. Confirme a precisão, sua evidência e o responsável pela verificação.`,
      "success",
    );
    byId("accuracy").focus();
  } catch (error) {
    setResult("geocoding-result", error.message, "error");
  }
}

function configurePropertyFields() {
  const type = byId("property-type").value;
  const controls = {
    "private-area-field": type === "APARTMENT",
    "built-area-field": type === "HOUSE" || type === "APARTMENT",
    "land-area-field": type === "HOUSE" || type === "LAND",
  };
  for (const [fieldId, visible] of Object.entries(controls)) {
    const label = byId(fieldId);
    label.classList.toggle("hidden", !visible);
    const input = label.querySelector("input");
    input.disabled = !visible;
    input.required = (type === "APARTMENT" && fieldId === "private-area-field") ||
      (type === "HOUSE" && ["built-area-field", "land-area-field"].includes(fieldId)) ||
      (type === "LAND" && fieldId === "land-area-field");
    if (!visible) input.value = "";
  }
  for (const field of document.querySelectorAll(".residential-field")) {
    field.classList.toggle("hidden", type === "LAND");
    field.querySelector("input").disabled = type === "LAND";
  }
}

function buildPayload() {
  const cityOption = byId("city").selectedOptions[0];
  const conflict = byId("has-conflict").checked;
  if (
    state.geocodingAddressSignature &&
    state.geocodingAddressSignature !== addressSignature()
  ) {
    throw new Error("O endereço mudou após a geocodificação. Localize-o novamente.");
  }
  const manualEvidence = byId("evidence-reference").value.trim();
  const evidenceReference = state.geocodingEvidence
    ? `${state.geocodingEvidence};PRECISAO:${manualEvidence}`
    : manualEvidence;
  return {
    external_order_id: byId("external-order-id").value.trim(),
    property: {
      property_type: byId("property-type").value,
      state: cityOption.dataset.state,
      city: cityOption.dataset.name,
      city_ibge_code: cityOption.value,
      postal_code: byId("postal-code").value.trim(),
      neighborhood: byId("neighborhood").value.trim(),
      street: byId("street").value.trim(),
      number: byId("number").value.trim(),
      complement: byId("complement").value.trim() || null,
      private_area_m2: nullableNumber("private-area"),
      built_area_m2: nullableNumber("built-area"),
      land_area_m2: nullableNumber("land-area"),
      bedrooms: nullableNumber("bedrooms"),
      bathrooms: nullableNumber("bathrooms"),
      parking_spaces: nullableNumber("parking-spaces"),
    },
    conflict_of_interest: conflict ? {
      has_conflict: true,
      conflict_type: byId("conflict-type").value.trim(),
      description: byId("conflict-description").value.trim(),
      identified_by: byId("conflict-identified-by").value.trim(),
    } : { has_conflict: false },
    location_confirmation: {
      is_confirmed: true,
      confirmation_method: byId("confirmation-method").value,
      evidence_reference: evidenceReference,
      verified_by: byId("verified-by").value.trim(),
      geocoding_audit_id: state.geocodingAuditId || null,
      latitude: Number(byId("latitude").value),
      longitude: Number(byId("longitude").value),
      accuracy_meters: Number(byId("accuracy").value),
    },
  };
}

async function createOrder(event) {
  event.preventDefault();
  clearResult("create-result");
  try {
    const response = await api("/orders", { method: "POST", body: JSON.stringify(buildPayload()) });
    const order = await response.json();
    const suffix = order.status === "REFUSED" ? " Acesse o motivo na lista abaixo." : "";
    setResult("create-result", `Ordem ${order.external_order_id} criada com status ${order.status}.${suffix}`, order.status === "REFUSED" ? "error" : "success");
    await refreshOrders();
  } catch (error) {
    setResult("create-result", error.message, "error");
  }
}

function actionButton(label, action, id) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "button quiet small";
  button.textContent = label;
  button.addEventListener("click", () => action(id));
  return button;
}

async function refreshOrders() {
  clearResult("orders-result");
  const body = byId("orders-body");
  try {
    const response = await api("/orders?limit=100");
    const listing = await response.json();
    body.replaceChildren();
    if (!listing.items.length) {
      body.innerHTML = '<tr><td colspan="5">Nenhuma ordem cadastrada.</td></tr>';
      return;
    }
    for (const order of listing.items) {
      const row = document.createElement("tr");
      const values = [order.external_order_id, `${order.property.city}/${order.property.state}`, order.property.property_type];
      for (const value of values) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.append(cell);
      }
      const statusCell = document.createElement("td");
      const status = document.createElement("span");
      status.className = `status status-${order.status}`;
      status.textContent = order.status;
      statusCell.append(status);
      row.append(statusCell);
      const actions = document.createElement("td");
      actions.className = "row-actions";
      if (["RECEIVED", "VALIDATING_INPUT", "ACCEPTED", "QUEUED", "PROCESSING", "FAILED"].includes(order.status)) {
        actions.append(actionButton("Processar", processOrder, order.internal_order_id));
      }
      if (order.status === "COMPLETED") {
        actions.append(actionButton("PDF", (id) => downloadReport(id, "pdf"), order.internal_order_id));
        actions.append(actionButton("CSV", (id) => downloadReport(id, "csv"), order.internal_order_id));
      }
      if (order.status === "REFUSED") actions.append(actionButton("Ver recusa", showRefusal, order.internal_order_id));
      row.append(actions);
      body.append(row);
    }
  } catch (error) {
    body.innerHTML = '<tr><td colspan="5">A lista não pôde ser carregada.</td></tr>';
    setResult("orders-result", error.message, "error");
  }
}

async function processOrder(id) {
  try {
    const response = await api(`/orders/${id}/process`, { method: "POST" });
    const result = await response.json();
    if (result.outcome === "COMPLETED") {
      const value = Number(result.valuation.estimated_value).toLocaleString(
        "pt-BR",
        { minimumFractionDigits: 2 },
      );
      setResult("orders-result", `Avaliação concluída: R$ ${value}.`, "success");
    } else if (result.outcome === "REFUSED") {
      setResult("orders-result", `${result.refusal.reason_code} · ${result.refusal.message}`, "error");
    } else {
      setResult("orders-result", "OS cancelada porque o prazo máximo de resposta foi excedido.", "error");
    }
    await refreshOrders();
  } catch (error) {
    setResult("orders-result", error.message, "error");
    await refreshOrders();
  }
}

async function showRefusal(id) {
  try {
    const response = await api(`/orders/${id}/refusal`);
    const refusal = await response.json();
    setResult("orders-result", `${refusal.reason_code} · ${refusal.message}`, "error");
  } catch (error) { setResult("orders-result", error.message, "error"); }
}

function reportFilename(response, fallback) {
  const disposition = response.headers.get("Content-Disposition") || "";
  const encoded = disposition.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
  const quoted = disposition.match(/filename\s*=\s*"([^"]+)"/i);
  const plain = disposition.match(/filename\s*=\s*([^;]+)/i);
  let candidate = encoded?.[1] || quoted?.[1] || plain?.[1] || "";

  if (encoded && candidate) {
    try { candidate = decodeURIComponent(candidate); } catch (_) {
      // Mantém o nome literal quando o servidor enviar codificação inválida.
    }
  }

  const basename = candidate.split(/[\\/]/).pop()
    ?.replace(/[\u0000-\u001f\u007f]/g, "").trim();
  return basename || fallback;
}

async function downloadReport(id, extension) {
  try {
    const response = await api(`/orders/${id}/valuation/report.${extension}`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = reportFilename(response, `avaliacao-${id}.${extension}`);
    anchor.click();
    URL.revokeObjectURL(url);
  } catch (error) { setResult("orders-result", error.message, "error"); }
}

function generateOrderId() {
  const now = new Date();
  const stamp = now.toISOString().replace(/[-:TZ.]/g, "").slice(0, 14);
  byId("external-order-id").value = `TESTE-AVM-${stamp}`;
}

byId("test-connection").addEventListener("click", async () => {
  try {
    const response = await api("/orders?limit=1");
    const body = await response.json();
    setResult("connection-result", `Acesso autorizado. ${body.total} ordem(ns) disponível(is).`, "success");
    await refreshOrders();
  } catch (error) { setResult("connection-result", error.message, "error"); }
});
byId("clear-key").addEventListener("click", () => {
  byId("client-key").value = "";
  state.key = "";
  setResult("connection-result", "Chave removida da memória da página.", "info");
});
byId("property-type").addEventListener("change", configurePropertyFields);
byId("has-conflict").addEventListener("change", (event) => {
  byId("conflict-details").classList.toggle("hidden", !event.target.checked);
  for (const input of byId("conflict-details").querySelectorAll("input, textarea")) input.required = event.target.checked;
});
byId("generate-order-id").addEventListener("click", generateOrderId);
byId("resolve-address").addEventListener("click", resolveAddress);
for (const id of ["city", "postal-code", "street", "number", "complement"]) {
  byId(id).addEventListener("change", () => {
    if (state.geocodingAuditId) resetAutomaticGeocoding();
  });
}
byId("confirmation-method").addEventListener("change", (event) => {
  if (state.geocodingAuditId && event.target.value !== "CNEFE_IBGE") {
    const method = event.target.value;
    resetAutomaticGeocoding();
    byId("confirmation-method").value = method;
  }
});
byId("order-form").addEventListener("submit", createOrder);
byId("refresh-orders").addEventListener("click", refreshOrders);
byId("order-form").addEventListener("reset", () => {
  resetAutomaticGeocoding();
  setTimeout(configurePropertyFields);
});

checkHealth();
loadCities();
configurePropertyFields();
generateOrderId();
