(function () {
  const citiesByCountry = {
    CO: ["Medellín", "Bogotá", "Cali"],
    US: ["Miami", "Orlando"],
  };

  const locationsByCity = {
    "CO|Medellín": ["Brasaland El Poblado", "Brasaland Laureles", "Brasaland Envigado", "Brasaland Sabaneta"],
    "CO|Bogotá": ["Brasaland Usaquén", "Brasaland Chapinero", "Brasaland Zona Rosa"],
    "CO|Cali": ["Brasaland Granada", "Brasaland Ciudad Jardín", "Brasaland Unicentro"],
    "US|Miami": ["Brasaland Brickell", "Brasaland Coral Gables"],
    "US|Orlando": ["Brasaland Downtown", "Brasaland International Drive"],
  };

  const messages = {
    fullName: "Ingresa tu nombre completo (nombre y apellido)",
    email: "Ingresa un email válido (ejemplo: <nombre@correo.com>)",
    phone: "El teléfono debe incluir código de país (ejemplo: +57 300 123 4567 o +1 305 123 4567)",
    country: "Selecciona tu país",
    city: "Selecciona tu ciudad",
    discovery: "Cuéntanos cómo conociste Brasaland",
    birthDate: "Debes ser mayor de 18 años para registrarte en Brasa Points",
    terms: "Debes aceptar los términos del programa Brasa Points para continuar",
  };

  function isValidEmail(value) {
    return /^[A-Z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?\.)+[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?$/i.test(value.trim());
  }

  function hasFullName(value) {
    return value.trim().split(/\s+/).filter((part) => /[\p{L}\p{M}]/u.test(part)).length >= 2;
  }

  function isValidPhone(value, country) {
    const expectedCode = country === "CO" ? "57" : country === "US" ? "1" : null;
    if (!expectedCode) return false;
    const phonePattern = expectedCode === "57" ? /^\+57(?:[ -]?\d){10}$/ : /^\+1(?:[ -]?\d){10}$/;
    return phonePattern.test(value.trim());
  }

  function isAdult(value, today = new Date()) {
    if (!value) return false;
    const birthDate = new Date(`${value}T00:00:00`);
    if (Number.isNaN(birthDate.getTime()) || birthDate >= today) return false;
    let age = today.getFullYear() - birthDate.getFullYear();
    const beforeBirthday = today.getMonth() < birthDate.getMonth() ||
      (today.getMonth() === birthDate.getMonth() && today.getDate() < birthDate.getDate());
    if (beforeBirthday) age -= 1;
    return age > 18;
  }

  function validateField(field, form) {
    const value = field.type === "checkbox" ? field.checked : field.value.trim();
    switch (field.name) {
      case "fullName":
        return hasFullName(value) ? "" : messages.fullName;
      case "email":
        return isValidEmail(value) ? "" : messages.email;
      case "phone":
        return isValidPhone(value, form.elements.country.value) ? "" : messages.phone;
      case "country":
        return value ? "" : messages.country;
      case "city":
        return value && citiesByCountry[form.elements.country.value]?.includes(value) ? "" : messages.city;
      case "discovery":
        return value ? "" : messages.discovery;
      case "birthDate":
        return isAdult(value) ? "" : messages.birthDate;
      case "terms":
        return value ? "" : messages.terms;
      default:
        return "";
    }
  }

  function setFieldError(field, message) {
    const errorElement = document.getElementById(`${field.id}-error`);
    field.setAttribute("aria-invalid", message ? "true" : "false");
    if (errorElement) errorElement.textContent = message;
  }

  function replaceOptions(select, placeholder, options) {
    select.replaceChildren(new Option(placeholder, ""));
    for (const value of options) select.add(new Option(value, value));
    select.disabled = options.length === 0;
  }

  function initializeForm() {
    const form = document.getElementById("registration-form");
    if (!form) return;

    const country = form.elements.country;
    const city = form.elements.city;
    const favoriteLocation = form.elements.favoriteLocation;
    const summary = document.getElementById("form-error-summary");
    const success = document.getElementById("registration-success");
    const requiredFields = ["fullName", "email", "phone", "country", "city", "discovery", "birthDate", "terms"]
      .map((name) => form.elements[name]);
    const touched = new Set();

    function updateCityOptions() {
      replaceOptions(city, country.value ? "Selecciona tu ciudad" : "Primero selecciona tu país", citiesByCountry[country.value] || []);
      replaceOptions(favoriteLocation, "Selecciona una ubicación (opcional)", []);
      city.value = "";
      favoriteLocation.value = "";
      setFieldError(city, "");
      city.removeAttribute("aria-invalid");
      favoriteLocation.removeAttribute("aria-invalid");
    }

    function updateFavoriteOptions() {
      const key = `${country.value}|${city.value}`;
      replaceOptions(favoriteLocation, "Selecciona una ubicación (opcional)", locationsByCity[key] || []);
      favoriteLocation.value = "";
    }

    function validateTouchedField(field) {
      if (!field || !touched.has(field.name)) return;
      setFieldError(field, validateField(field, form));
    }

    country.addEventListener("change", () => {
      updateCityOptions();
      validateTouchedField(country);
      validateTouchedField(form.elements.phone);
      summary.textContent = "";
    });

    city.addEventListener("change", () => {
      updateFavoriteOptions();
      touched.add("city");
      setFieldError(city, validateField(city, form));
      summary.textContent = "";
    });

    for (const field of requiredFields) {
      field.addEventListener("blur", () => {
        touched.add(field.name);
        setFieldError(field, validateField(field, form));
      });
      field.addEventListener(field.type === "checkbox" || field.tagName === "SELECT" ? "change" : "input", () => {
        if (touched.has(field.name)) setFieldError(field, validateField(field, form));
        summary.textContent = "";
      });
    }

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      let firstInvalidField = null;
      let errorCount = 0;

      for (const field of requiredFields) {
        touched.add(field.name);
        const message = validateField(field, form);
        setFieldError(field, message);
        if (message) {
          errorCount += 1;
          firstInvalidField ||= field;
        }
      }

      if (errorCount) {
        summary.textContent = `Revisa los ${errorCount} campos marcados antes de continuar.`;
        firstInvalidField.focus();
        success.classList.add("hidden");
        return;
      }

      summary.textContent = "";
      success.classList.remove("hidden");
      success.focus();
    });

    form.addEventListener("reset", () => {
      window.setTimeout(() => {
        updateCityOptions();
        touched.clear();
        for (const field of requiredFields) {
          setFieldError(field, "");
          field.removeAttribute("aria-invalid");
        }
        summary.textContent = "";
        success.classList.add("hidden");
      }, 0);
    });
  }

  const api = { citiesByCountry, locationsByCity, messages, isValidEmail, hasFullName, isValidPhone, isAdult };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof document !== "undefined") initializeForm();
})();
