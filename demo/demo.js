"use strict";

const contacts = [
  { id: 1, nombre: "Sofía", apellido: "Mendoza", telefono: "+507 6001-2345", email: "sofia.mendoza@example.com", role: "Diseñadora de producto" },
  { id: 2, nombre: "Mateo", apellido: "Castillo", telefono: "+507 6002-3456", email: "mateo.castillo@example.com", role: "Desarrollador" },
  { id: 3, nombre: "Valentina", apellido: "Ríos", telefono: "+507 6003-4567", email: "valentina.rios@example.com", role: "Coordinadora de proyectos" },
  { id: 4, nombre: "Daniel", apellido: "Vega", telefono: "+507 6004-5678", email: "daniel.vega@example.com", role: "Analista de soporte" },
  { id: 5, nombre: "Camila", apellido: "Navarro", telefono: "+507 6005-6789", email: "camila.navarro@example.com", role: "Administradora" },
];

let selectedId = contacts[0].id;
let editingId = null;
let noticeTimer;

const list = document.getElementById("contact-list");
const detail = document.getElementById("contact-detail");
const search = document.getElementById("search");
const addDialog = document.getElementById("add-dialog");
const editDialog = document.getElementById("edit-dialog");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

function initials(name) {
  return escapeHtml((name.trim()[0] || "?").toLocaleUpperCase("es"));
}

function render() {
  const query = search.value.trim().toLocaleLowerCase("es");
  const matches = contacts.filter((contact) =>
    Object.values(contact).join(" ").toLocaleLowerCase("es").includes(query)
  );
  if (!matches.some((contact) => contact.id === selectedId)) {
    selectedId = matches.length ? matches[0].id : null;
  }

  document.getElementById("sidebar-count").textContent = contacts.length;
  document.getElementById("result-count").textContent =
    `${matches.length} resultado${matches.length === 1 ? "" : "s"}`;
  document.getElementById("footer-count").innerHTML =
    `Mostrando <strong>${matches.length}</strong> de <strong>${contacts.length}</strong> contactos`;

  list.innerHTML = matches.length
    ? matches.map((contact, index) => {
      const name = `${contact.nombre} ${contact.apellido}`.trim();
      return `<button class="contact-row${contact.id === selectedId ? " selected" : ""}" type="button" data-contact="${contact.id}" aria-pressed="${contact.id === selectedId}">
        <span class="contact-avatar avatar-color-${index % 6}">${initials(name)}</span>
        <span class="contact-copy"><strong>${escapeHtml(name)}</strong><span>${escapeHtml(contact.role || "Sin cargo asignado")}</span></span>
        <svg class="row-arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>
      </button>`;
    }).join("")
    : `<div class="empty-state"><span class="empty-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg></span><strong>${query ? "No encontramos coincidencias" : "Aún no hay contactos"}</strong><span>${query ? "Prueba con otro nombre, correo o cargo." : "Agrega una persona para probar la demo."}</span></div>`;

  list.querySelectorAll("[data-contact]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedId = Number(button.dataset.contact);
      render();
    });
  });

  const selected = matches.find((contact) => contact.id === selectedId);
  if (!selected) {
    detail.innerHTML = `<div class="detail-empty"><span class="empty-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z"/></svg></span><strong>Selecciona un contacto</strong><span>Elige una persona de la lista para consultar sus datos.</span></div>`;
    return;
  }

  const name = `${selected.nombre} ${selected.apellido}`.trim();
  const avatarColor = contacts.findIndex((contact) => contact.id === selected.id) % 6;
  detail.innerHTML = `<div class="detail-topline"><span>PERFIL DEL CONTACTO</span><button class="icon-button" type="button" data-edit aria-label="Editar contacto"><svg viewBox="0 0 24 24"><path d="m15 5 4 4M4 20l4-.8L19 8a2.1 2.1 0 0 0-3-3L5 16l-1 4Z"/></svg></button></div>
    <div class="profile-hero"><div class="detail-avatar avatar-color-${avatarColor}">${initials(name)}</div><h2>${escapeHtml(name)}</h2><span class="role-badge"><i></i>${escapeHtml(selected.role || "Sin cargo asignado")}</span><span class="contact-id">ID de contacto · ${selected.id}</span></div>
    <div class="detail-divider"></div><div class="detail-section-title">INFORMACIÓN DE CONTACTO</div>
    <div class="info-list">
      <div class="info-item"><span class="info-icon phone-icon"><svg viewBox="0 0 24 24"><path d="M7.4 3.8 9.6 3a1.7 1.7 0 0 1 2.1 1l1 2.5a1.7 1.7 0 0 1-.5 2l-1.4 1.1a14 14 0 0 0 5.6 5.6l1.1-1.4a1.7 1.7 0 0 1 2-.5l2.5 1a1.7 1.7 0 0 1 1 2.1l-.8 2.2a2.6 2.6 0 0 1-2.7 1.7A18.7 18.7 0 0 1 3.7 6.5a2.6 2.6 0 0 1 1.7-2.7Z"/></svg></span><span><small>TELÉFONO</small><strong>${escapeHtml(selected.telefono || "No disponible")}</strong></span></div>
      <div class="info-item"><span class="info-icon email-icon"><svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg></span><span><small>CORREO ELECTRÓNICO</small><strong>${escapeHtml(selected.email || "No disponible")}</strong></span></div>
      <div class="info-item"><span class="info-icon role-icon"><svg viewBox="0 0 24 24"><rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18m-11 0v2h4v-2"/></svg></span><span><small>CARGO</small><strong>${escapeHtml(selected.role || "No disponible")}</strong></span></div>
    </div><button class="edit-button" type="button" data-edit><svg viewBox="0 0 24 24"><path d="m15 5 4 4M4 20l4-.8L19 8a2.1 2.1 0 0 0-3-3L5 16l-1 4Z"/></svg>Editar contacto</button>`;

  detail.querySelectorAll("[data-edit]").forEach((button) =>
    button.addEventListener("click", openEditDialog)
  );
}

function showNotice(message) {
  const status = document.getElementById("status-message");
  status.innerHTML = `<div class="flash success">${escapeHtml(message)}</div>`;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => { status.innerHTML = ""; }, 4000);
}

function formValues(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function openEditDialog() {
  const contact = contacts.find((item) => item.id === selectedId);
  if (!contact) return;
  editingId = contact.id;
  const form = document.getElementById("edit-form");
  Object.keys(contact).forEach((key) => {
    if (form.elements.namedItem(key)) form.elements.namedItem(key).value = contact[key];
  });
  editDialog.showModal();
}

search.addEventListener("input", render);

document.getElementById("add-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const values = formValues(event.currentTarget);
  const id = Math.max(0, ...contacts.map((contact) => contact.id)) + 1;
  contacts.unshift({ id, ...values });
  selectedId = id;
  event.currentTarget.reset();
  addDialog.close();
  search.value = "";
  render();
  showNotice("Contacto agregado a la demo. No se guardará al cerrar o recargar la página.");
});

document.getElementById("edit-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const contact = contacts.find((item) => item.id === editingId);
  if (!contact) return;
  Object.assign(contact, formValues(event.currentTarget));
  selectedId = contact.id;
  editDialog.close();
  render();
  showNotice("Cambios aplicados en esta sesión de demostración.");
});

document.querySelectorAll("[data-open]").forEach((button) => {
  button.addEventListener("click", () => document.getElementById(button.dataset.open).showModal());
});
document.querySelectorAll(".contact-dialog").forEach((dialog) => {
  dialog.querySelectorAll(".dialog-close, .cancel-button").forEach((button) =>
    button.addEventListener("click", () => dialog.close())
  );
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
});

render();
