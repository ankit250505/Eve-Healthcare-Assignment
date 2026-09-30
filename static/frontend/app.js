const state = {
  accessToken: "",
  refreshToken: "",
  user: null,
  offerings: [],
  selectedOffering: null,
  selectedBooking: null,
  authMode: "login",
};

const els = {
  status: document.querySelector("#globalStatus"),
  session: document.querySelector("#sessionPill"),
  loginTab: document.querySelector("#loginTab"),
  signupTab: document.querySelector("#signupTab"),
  authPanel: document.querySelector("#auth-panel"),
  authForm: document.querySelector("#authForm"),
  authSubmit: document.querySelector("#authSubmit"),
  catalogueSearch: document.querySelector("#catalogueSearch"),
  catalogueList: document.querySelector("#catalogueList"),
  selectedOffering: document.querySelector("#selectedOffering"),
  bookingForm: document.querySelector("#bookingForm"),
  appointmentAt: document.querySelector("#appointmentAt"),
  checkoutSummary: document.querySelector("#checkoutSummary"),
  paySuccess: document.querySelector("#paySuccess"),
  payFail: document.querySelector("#payFail"),
  refreshBookings: document.querySelector("#refreshBookings"),
  bookingList: document.querySelector("#bookingList"),
};

function setStatus(message, type = "info") {
  els.status.textContent = message;
  els.status.dataset.type = type;
}

function setLoading(button, isLoading, label) {
  if (!button) return;
  button.disabled = isLoading;
  if (label) button.textContent = label;
}

function authHeaders(extra = {}) {
  return state.accessToken
    ? { ...extra, Authorization: `Bearer ${state.accessToken}` }
    : extra;
}

async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });
  const payload = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail || payload?.non_field_errors?.join(" ") || firstError(payload) || "Request failed.";
    throw new Error(detail);
  }
  return payload;
}

function firstError(payload) {
  if (!payload || typeof payload !== "object") return "";
  const first = Object.values(payload)[0];
  if (Array.isArray(first)) return first.join(" ");
  if (typeof first === "string") return first;
  return "";
}

function money(value) {
  return `INR ${Number(value).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function localOffsetIso(datetimeLocal) {
  return `${datetimeLocal}:00+05:30`;
}

function updateSession() {
  els.session.textContent = state.user ? state.user.email : "Signed out";
}

function setAuthMode(mode) {
  state.authMode = mode;
  const isSignup = mode === "signup";
  els.authPanel.classList.toggle("signup-mode", isSignup);
  els.loginTab.classList.toggle("active", !isSignup);
  els.signupTab.classList.toggle("active", isSignup);
  els.authSubmit.textContent = isSignup ? "Create account" : "Login";
}

async function loadOfferings() {
  els.catalogueList.innerHTML = `<div class="empty-state">Loading available tests...</div>`;
  try {
    const data = await apiFetch("/api/offerings/");
    state.offerings = data.results || data;
    renderOfferings();
    setStatus("Catalogue loaded. Select a test to continue.");
  } catch (error) {
    els.catalogueList.innerHTML = `<div class="empty-state">${error.message}</div>`;
    setStatus(error.message, "error");
  }
}

function renderOfferings() {
  const query = els.catalogueSearch.value.trim().toLowerCase();
  const filtered = state.offerings.filter((offering) => {
    const haystack = [
      offering.centre.name,
      offering.centre.city,
      offering.centre.address,
      offering.test.name,
      offering.test.code,
    ].join(" ").toLowerCase();
    return haystack.includes(query);
  });

  if (!filtered.length) {
    els.catalogueList.innerHTML = `<div class="empty-state">No matching tests found.</div>`;
    return;
  }

  els.catalogueList.innerHTML = filtered.map((offering) => `
    <article class="offering-card">
      <div>
        <h3>${escapeHtml(offering.test.name)}</h3>
        <p class="meta-line">${escapeHtml(offering.centre.name)} · ${escapeHtml(offering.centre.city)}</p>
        <p class="meta-line">${escapeHtml(offering.centre.address)}</p>
      </div>
      <div>
        <div class="price">${money(offering.price)}</div>
        <button class="button button-secondary" type="button" data-select-offering="${offering.id}">Select</button>
      </div>
    </article>
  `).join("");
}

function selectOffering(id) {
  state.selectedOffering = state.offerings.find((offering) => offering.id === Number(id));
  if (!state.selectedOffering) return;
  els.selectedOffering.innerHTML = `
    <strong>${escapeHtml(state.selectedOffering.test.name)}</strong><br>
    ${escapeHtml(state.selectedOffering.centre.name)}, ${escapeHtml(state.selectedOffering.centre.city)}<br>
    <span class="price">${money(state.selectedOffering.price)}</span>
  `;
  document.querySelector("#booking").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function handleAuth(event) {
  event.preventDefault();
  const form = new FormData(els.authForm);
  const isSignup = state.authMode === "signup";
  const body = {
    email: form.get("email"),
    password: form.get("password"),
  };
  if (isSignup) {
    body.first_name = form.get("first_name");
    body.last_name = form.get("last_name");
  }

  setLoading(els.authSubmit, true, isSignup ? "Creating..." : "Signing in...");
  try {
    if (isSignup) {
      await apiFetch("/api/auth/signup/", { method: "POST", body: JSON.stringify(body) });
    }
    const tokens = await apiFetch("/api/auth/login/", {
      method: "POST",
      body: JSON.stringify({ email: body.email, password: body.password }),
    });
    state.accessToken = tokens.access;
    state.refreshToken = tokens.refresh;
    state.user = await apiFetch("/api/auth/me/", { headers: authHeaders() });
    updateSession();
    setStatus(`Signed in as ${state.user.email}.`);
    await loadBookings();
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setLoading(els.authSubmit, false, isSignup ? "Create account" : "Login");
  }
}

async function createBooking(event) {
  event.preventDefault();
  if (!state.accessToken) {
    setStatus("Please sign in before creating a booking.", "error");
    return;
  }
  if (!state.selectedOffering) {
    setStatus("Select a test from the catalogue first.", "error");
    return;
  }
  if (!els.appointmentAt.value) {
    setStatus("Choose an appointment date and time.", "error");
    return;
  }

  const submit = document.querySelector("#bookingSubmit");
  setLoading(submit, true, "Creating booking...");
  try {
    const booking = await apiFetch("/api/bookings/", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        offering_id: state.selectedOffering.id,
        appointment_at: localOffsetIso(els.appointmentAt.value),
      }),
    });
    state.selectedBooking = booking;
    renderCheckout();
    setStatus("Booking created. You can now run the simulated payment.");
    await loadBookings();
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setLoading(submit, false, "Create booking");
  }
}

function renderCheckout() {
  if (!state.selectedBooking) {
    els.checkoutSummary.textContent = "Create a booking to enable payment simulation.";
    els.paySuccess.disabled = true;
    els.payFail.disabled = true;
    return;
  }

  const booking = state.selectedBooking;
  els.checkoutSummary.innerHTML = `
    <strong>${escapeHtml(booking.test_name)}</strong><br>
    ${escapeHtml(booking.centre_name)} · ${formatDate(booking.appointment_at)}<br>
    <span class="price">${money(booking.amount)}</span>
    <span class="status-badge status-${booking.status}">${booking.status}</span>
  `;
  const canPay = booking.status === "PENDING";
  els.paySuccess.disabled = !canPay;
  els.payFail.disabled = !canPay;
}

async function simulatePayment(outcome) {
  if (!state.selectedBooking) return;
  const button = outcome === "SUCCESS" ? els.paySuccess : els.payFail;
  setLoading(button, true, outcome === "SUCCESS" ? "Processing..." : "Failing...");
  try {
    const payment = await apiFetch("/api/payments/", {
      method: "POST",
      headers: authHeaders({ "Idempotency-Key": `ui-${state.selectedBooking.id}-${outcome}` }),
      body: JSON.stringify({
        booking_id: state.selectedBooking.id,
        simulated_outcome: outcome,
      }),
    });
    setStatus(`Payment ${payment.status.toLowerCase()}. Booking list refreshed.`);
    await loadBookings();
    const refreshed = await apiFetch(`/api/bookings/${state.selectedBooking.id}/`, { headers: authHeaders() });
    state.selectedBooking = refreshed;
    renderCheckout();
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setLoading(button, false, outcome === "SUCCESS" ? "Mark success" : "Mark failed");
  }
}

async function loadBookings() {
  if (!state.accessToken) {
    els.bookingList.innerHTML = `<div class="empty-state">Sign in to see your bookings.</div>`;
    return;
  }

  els.bookingList.innerHTML = `<div class="empty-state">Loading bookings...</div>`;
  try {
    const data = await apiFetch("/api/bookings/", { headers: authHeaders() });
    renderBookings(data.results || data);
  } catch (error) {
    els.bookingList.innerHTML = `<div class="empty-state">${error.message}</div>`;
    setStatus(error.message, "error");
  }
}

function renderBookings(bookings) {
  if (!bookings.length) {
    els.bookingList.innerHTML = `<div class="empty-state">No bookings yet.</div>`;
    return;
  }

  els.bookingList.innerHTML = bookings.map((booking) => `
    <article class="booking-card">
      <div>
        <span class="status-badge status-${booking.status}">${booking.status}</span>
        <h3>${escapeHtml(booking.test_name)}</h3>
        <p class="meta-line">${escapeHtml(booking.centre_name)} · ${escapeHtml(booking.centre_city)}</p>
        <p class="meta-line">${formatDate(booking.appointment_at)} · ${money(booking.amount)}</p>
      </div>
      <div class="booking-actions">
        <button class="button button-secondary" type="button" data-use-booking="${booking.id}">Use for checkout</button>
        <button class="button button-danger" type="button" data-cancel-booking="${booking.id}" ${booking.status === "CONFIRMED" || booking.status === "CANCELLED" ? "disabled" : ""}>Cancel</button>
      </div>
    </article>
  `).join("");
}

async function cancelBooking(id) {
  try {
    const booking = await apiFetch(`/api/bookings/${id}/cancel/`, {
      method: "POST",
      headers: authHeaders(),
    });
    if (state.selectedBooking?.id === booking.id) {
      state.selectedBooking = booking;
      renderCheckout();
    }
    setStatus("Booking cancelled.");
    await loadBookings();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function useBooking(id) {
  try {
    state.selectedBooking = await apiFetch(`/api/bookings/${id}/`, { headers: authHeaders() });
    renderCheckout();
    document.querySelector(".checkout-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    setStatus(error.message, "error");
  }
}

function formatDate(value) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata",
  }).format(new Date(value));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

els.loginTab.addEventListener("click", () => setAuthMode("login"));
els.signupTab.addEventListener("click", () => setAuthMode("signup"));
els.authForm.addEventListener("submit", handleAuth);
els.catalogueSearch.addEventListener("input", renderOfferings);
els.catalogueList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-select-offering]");
  if (button) selectOffering(button.dataset.selectOffering);
});
els.bookingForm.addEventListener("submit", createBooking);
els.paySuccess.addEventListener("click", () => simulatePayment("SUCCESS"));
els.payFail.addEventListener("click", () => simulatePayment("FAILED"));
els.refreshBookings.addEventListener("click", loadBookings);
els.bookingList.addEventListener("click", (event) => {
  const cancel = event.target.closest("[data-cancel-booking]");
  const use = event.target.closest("[data-use-booking]");
  if (cancel) cancelBooking(cancel.dataset.cancelBooking);
  if (use) useBooking(use.dataset.useBooking);
});

setAuthMode("login");
renderCheckout();
loadOfferings();
loadBookings();
