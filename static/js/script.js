// Navbar scroll effect
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => {
  navbar.classList.toggle('scrolled', window.scrollY > 50);
  updateActiveNav();
});

// Mobile hamburger
const hamburger = document.getElementById('hamburger');
const navLinks = document.getElementById('navLinks');

hamburger.addEventListener('click', () => {
  hamburger.classList.toggle('open');
  navLinks.classList.toggle('open');
});

navLinks.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', () => {
    hamburger.classList.remove('open');
    navLinks.classList.remove('open');
  });
});

// Highlight active nav link on scroll
function updateActiveNav() {
  const sections = document.querySelectorAll('section[id]');
  let current = '';
  sections.forEach(sec => {
    if (window.scrollY >= sec.offsetTop - 140) current = sec.id;
  });
  navLinks.querySelectorAll('a').forEach(link => {
    link.classList.toggle('active', link.getAttribute('href') === `#${current}`);
  });
}

// Scroll fade-in animations
const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      setTimeout(() => entry.target.classList.add('visible'), i * 80);
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));

// Dynamic service dropdown based on vehicle type
const vehicleTypeEl = document.getElementById('vehicleType');
const vehicleBrandEl = document.getElementById('vehicleBrand');
const vehicleModelEl = document.getElementById('vehicleModel');
const serviceSelectEl = document.getElementById('serviceSelect');
let VEHICLE_CATALOG = {};

const CAR_SERVICES = [
  'Basic Wash – ₹499',
  'Foam Wash – ₹699',
  'Interior Cleaning – ₹999',
  'Wax Polish – ₹1,499',
  'Deep Cleaning – ₹2,999',
];

const BIKE_SERVICES = [
  'Bike Foam Wash – ₹199',
  'Bike Deep Wash – ₹299',
];

vehicleTypeEl.addEventListener('change', () => {
  serviceSelectEl.innerHTML = '<option value="">Select service</option>';
  vehicleBrandEl.innerHTML = '<option value="">Select brand</option>';
  vehicleModelEl.innerHTML = '<option value="">Select brand first</option>';

  const brands = Object.keys(VEHICLE_CATALOG[vehicleTypeEl.value] || {});
  brands.forEach(brand => {
    const opt = document.createElement('option');
    opt.value = brand;
    opt.textContent = brand;
    vehicleBrandEl.appendChild(opt);
  });

  const list = vehicleTypeEl.value === 'Car' ? CAR_SERVICES
             : vehicleTypeEl.value === 'Bike' ? BIKE_SERVICES : [];
  list.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s;
    opt.textContent = s;
    serviceSelectEl.appendChild(opt);
  });
});

vehicleBrandEl.addEventListener('change', () => {
  vehicleModelEl.innerHTML = '<option value="">Select car/bike name</option>';
  const models = (VEHICLE_CATALOG[vehicleTypeEl.value] || {})[vehicleBrandEl.value] || [];
  models.forEach(model => {
    const opt = document.createElement('option');
    opt.value = model;
    opt.textContent = model;
    vehicleModelEl.appendChild(opt);
  });
});

const bookingForm = document.getElementById('bookingForm');
const formSuccess = document.getElementById('formSuccess');
const formAlert = document.getElementById('formAlert');
const submitBtn = document.getElementById('submitBtn');
const existingVehicleSelectEl = document.getElementById('existingVehicle');
const existingVehicleRow = document.getElementById('existingVehicleRow');

function clearExistingVehicleSelection() {
  if (!existingVehicleSelectEl) return;
  existingVehicleSelectEl.innerHTML = '<option value="">Select existing vehicle for this phone</option>';
  existingVehicleRow.style.display = 'none';
}

async function loadCustomerVehicles(phone) {
  if (!existingVehicleSelectEl) return;
  const normalizedPhone = normalizePhoneInput(phone.trim());
  if (!normalizedPhone) {
    clearExistingVehicleSelection();
    return;
  }

  try {
    const res = await fetch(`/api/customer-vehicles?phone=${encodeURIComponent(normalizedPhone)}`);
    if (!res.ok) throw new Error('Vehicle fetch failed');
    const vehicles = await res.json();
    if (!Array.isArray(vehicles) || vehicles.length === 0) {
      clearExistingVehicleSelection();
      return;
    }

    existingVehicleSelectEl.innerHTML = '<option value="">Select existing vehicle for this phone</option>';
    vehicles.forEach(vehicle => {
      const option = document.createElement('option');
      option.value = vehicle.id;
      option.textContent = `${vehicle.vehicle_type} ${vehicle.vehicle_brand ? vehicle.vehicle_brand + ' ' : ''}${vehicle.vehicle_model} (${vehicle.number_plate || 'No plate'})`;
      option.dataset.vehicleType = vehicle.vehicle_type;
      option.dataset.vehicleBrand = vehicle.vehicle_brand || '';
      option.dataset.vehicleModel = vehicle.vehicle_model;
      option.dataset.vehiclePlate = vehicle.number_plate || '';
      existingVehicleSelectEl.appendChild(option);
    });
    existingVehicleRow.style.display = 'flex';
  } catch {
    clearExistingVehicleSelection();
  }
}

if (bookingForm && bookingForm.phone) {
  bookingForm.phone.addEventListener('blur', () => loadCustomerVehicles(bookingForm.phone.value));
  bookingForm.phone.addEventListener('input', () => {
    if (existingVehicleRow && existingVehicleRow.style.display === 'flex') {
      clearExistingVehicleSelection();
    }
  });
}

if (existingVehicleSelectEl) {
  existingVehicleSelectEl.addEventListener('change', () => {
    const option = existingVehicleSelectEl.selectedOptions[0];
    if (!option || !option.value) {
      return;
    }
    vehicleTypeEl.value = option.dataset.vehicleType || '';
    vehicleBrandEl.innerHTML = `<option value="${option.dataset.vehicleBrand}">${option.dataset.vehicleBrand || 'Select brand'}</option>`;
    vehicleModelEl.innerHTML = `<option value="${option.dataset.vehicleModel}">${option.dataset.vehicleModel}</option>`;
    document.getElementById('fplate').value = option.dataset.vehiclePlate || '';
  });
}

async function loadVehicleCatalog() {
  try {
    const res = await fetch('/api/vehicle-catalog');
    VEHICLE_CATALOG = await res.json();
  } catch {
    VEHICLE_CATALOG = {};
  }
}

function normalizePhoneInput(value) {
  const digits = (value || '').replace(/\D/g, '');
  if (!digits) return '';
  let local = digits;
  if (digits.length === 11 && digits.startsWith('0')) {
    local = digits.slice(1);
  } else if (digits.length > 10) {
    local = digits.slice(-10);
  }
  if (local.length !== 10) {
    return value.trim();
  }
  return `+91${local}`;
}

loadVehicleCatalog();

// Set today as minimum date
const dateInput = document.querySelector('input[name="preferred_date"]');
if (dateInput) {
  dateInput.min = new Date().toISOString().split('T')[0];
}

// Booking form submission
bookingForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  formAlert.style.display = 'none';

  const normalizedPhone = normalizePhoneInput(bookingForm.phone.value.trim());
  if (normalizedPhone) {
    bookingForm.phone.value = normalizedPhone;
  }
  if (existingVehicleSelectEl && existingVehicleSelectEl.value) {
    const selected = existingVehicleSelectEl.selectedOptions[0];
    if (selected && selected.value) {
      bookingForm.vehicle_type.value = selected.dataset.vehicleType || bookingForm.vehicle_type.value;
      bookingForm.vehicle_brand.value = selected.dataset.vehicleBrand || bookingForm.vehicle_brand.value;
      bookingForm.vehicle_model.value = selected.dataset.vehicleModel || bookingForm.vehicle_model.value;
      bookingForm.vehicle_plate.value = selected.dataset.vehiclePlate || bookingForm.vehicle_plate.value;
    }
  }

  const data = {
    name: bookingForm.name.value.trim(),
    phone: bookingForm.phone.value.trim(),
    vehicle_type: bookingForm.vehicle_type.value,
    vehicle_brand: bookingForm.vehicle_brand.value,
    vehicle_model: bookingForm.vehicle_model.value.trim(),
    vehicle_plate: bookingForm.vehicle_plate.value.toUpperCase().replace(/[^A-Z0-9]/g, ''),
    service: bookingForm.service.value,
    preferred_date: bookingForm.preferred_date.value,
    preferred_time: bookingForm.preferred_time.value,
    pickup_address: bookingForm.pickup_address.value.trim(),
    payment_method: bookingForm.payment_method?.value || '',
  };

  const required = ['name', 'phone', 'vehicle_type', 'vehicle_brand', 'vehicle_model', 'service', 'preferred_date', 'preferred_time'];
  if (required.some(k => !data[k])) {
    formAlert.textContent = 'Please fill in all required fields.';
    formAlert.style.display = 'block';
    return;
  }

  submitBtn.disabled = true;
  submitBtn.querySelector('span').textContent = 'Submitting…';

  try {
    const res = await fetch('/api/booking', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const result = await res.json();

    if (result.success) {
      bookingForm.style.display = 'none';
      formSuccess.style.display = 'block';
    } else {
      throw new Error();
    }
  } catch {
    formAlert.textContent = 'Something went wrong. Please try again or WhatsApp us at +91 8197180012.';
    formAlert.style.display = 'block';
    submitBtn.disabled = false;
    submitBtn.querySelector('span').textContent = 'Confirm Booking';
  }
});

const membershipForm = document.getElementById('membershipForm');
const membershipSignup = document.getElementById('membershipSignup');
const membershipSuccess = document.getElementById('membershipSuccess');
const membershipFormAlert = document.getElementById('membershipFormAlert');

function openMembershipForm(id, name, price, description) {
  if (!membershipSignup) return;
  membershipSignup.hidden = false;
  membershipSuccess.style.display = 'none';
  membershipFormAlert.style.display = 'none';
  document.getElementById('membershipId').value = id;
  document.getElementById('selectedMembershipTitle').textContent = `${name} Plan`;
  document.getElementById('selectedMembershipDescription').textContent = `${description}`;
  document.getElementById('selectedMembershipAmount').textContent = `Amount: ₹${price} / month`;
  window.scrollTo({ top: membershipSignup.offsetTop - 80, behavior: 'smooth' });
}

function resetMembershipForm() {
  if (!membershipSignup) return;
  membershipForm.reset();
  membershipSignup.hidden = true;
  membershipSuccess.style.display = 'none';
  membershipFormAlert.style.display = 'none';
}

if (membershipForm) {
  membershipForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!membershipFormAlert) return;
    membershipFormAlert.style.display = 'none';

    const screenshotInput = document.getElementById('paymentScreenshot');
    const screenshotFile = screenshotInput?.files?.[0];
    const membershipId = Number(document.getElementById('membershipId').value || 0);
    const name = membershipForm.name.value.trim();
    const normalizedPhone = normalizePhoneInput(membershipForm.phone.value.trim());
    if (normalizedPhone) {
      membershipForm.phone.value = normalizedPhone;
    }
    const phone = membershipForm.phone.value.trim();
    const vehicleType = membershipForm.vehicle_type?.value || membershipForm.memberVehicle?.value || '';
    const notes = membershipForm.notes?.value.trim() || '';

    if (!name || !phone || !membershipId) {
      membershipFormAlert.textContent = 'Please complete your name, phone, and selected membership plan.';
      membershipFormAlert.style.display = 'block';
      return;
    }

    if (!screenshotFile) {
      membershipFormAlert.textContent = 'Please upload a payment screenshot after paying via UPI.';
      membershipFormAlert.style.display = 'block';
      return;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('phone', phone);
    formData.append('membership_id', String(membershipId));
    formData.append('payment_method', 'UPI');
    formData.append('notes', notes);
    formData.append('screenshot', screenshotFile);

    try {
      const res = await fetch('/api/membership', {
        method: 'POST',
        body: formData,
      });
      const result = await res.json();

      if (result.success) {
        membershipSignup.hidden = true;
        membershipSuccess.style.display = 'block';
        membershipForm.reset();
      } else {
        throw new Error(result.message || 'Submission failed');
      }
    } catch {
      membershipFormAlert.textContent = 'Failed to submit membership. Please try again or WhatsApp us.';
      membershipFormAlert.style.display = 'block';
    }
  });
}

function appendAiChatMessage(text, role = 'bot') {
  const messagesEl = document.getElementById('aiChatMessages');
  if (!messagesEl) return;
  const messageEl = document.createElement('div');
  messageEl.className = `ai-chat-message ${role}`;
  messageEl.textContent = text;
  messagesEl.appendChild(messageEl);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setupAiChat() {
  const toggle = document.getElementById('aiChatToggle');
  const panel = document.getElementById('aiChatPanel');
  const closeBtn = document.getElementById('aiChatClose');
  const form = document.getElementById('aiChatForm');
  const input = document.getElementById('aiChatInput');

  if (!toggle || !panel || !closeBtn || !form || !input) return;

  toggle.addEventListener('click', () => {
    panel.classList.toggle('hidden');
    input.focus();
  });

  closeBtn.addEventListener('click', () => {
    panel.classList.add('hidden');
  });

  const openLink = document.getElementById('aiChatOpenLink');
  if (openLink) {
    openLink.addEventListener('click', () => {
      panel.classList.remove('hidden');
      input.focus();
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) return;

    appendAiChatMessage(question, 'user');
    input.value = '';
    input.disabled = true;
    appendAiChatMessage('Typing...', 'bot');

    try {
      const res = await fetch('/api/ai-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });
      const result = await res.json();
      const botMessages = document.querySelectorAll('.ai-chat-message.bot');
      if (botMessages.length) {
        botMessages[botMessages.length - 1].textContent = res.ok && result.success
          ? result.answer
          : 'Sorry, I could not get a response. Please try again later.';
      } else {
        appendAiChatMessage('Sorry, I could not get a response. Please try again later.', 'bot');
      }
    } catch {
      appendAiChatMessage('Unable to connect to AI assistant. Please try again later.', 'bot');
    } finally {
      input.disabled = false;
      input.focus();
    }
  });
}

function resetForm() {
  bookingForm.reset();
  bookingForm.style.display = 'block';
  formSuccess.style.display = 'none';
  formAlert.style.display = 'none';
  vehicleBrandEl.innerHTML = '<option value="">Select vehicle type first</option>';
  vehicleModelEl.innerHTML = '<option value="">Select brand first</option>';
  serviceSelectEl.innerHTML = '<option value="">Select service</option>';
  submitBtn.disabled = false;
  submitBtn.querySelector('span').textContent = 'Confirm Booking';
}

function attachMembershipPlanListeners() {
  document.querySelectorAll('.plan-card[data-action="open-membership"]').forEach(card => {
    card.addEventListener('click', event => {
      const buttonClicked = event.target.closest('button');
      if (buttonClicked) {
        event.preventDefault();
      }
      openMembershipForm(
        Number(card.dataset.id),
        card.dataset.name,
        Number(card.dataset.price),
        card.dataset.description
      );
    });
  });
}

attachMembershipPlanListeners();
setupAiChat();
fillMembershipPhoneFromUrl();

function fillMembershipPhoneFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const phone = params.get('phone') || params.get('membership_phone');
  if (!phone) return;

  const phoneInput = document.getElementById('memberPhone');
  if (phoneInput) {
    phoneInput.value = phone;
  }

  if (window.location.hash === '#membership') {
    const membershipSection = document.getElementById('membership');
    if (membershipSection) {
      membershipSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }
}
