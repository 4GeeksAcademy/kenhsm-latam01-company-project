export function Hero(context) {
  return `
    <header class="hero">
      <p class="eyebrow">${context.brand}</p>
      <h1>${context.tagline}</h1>
      <p class="subtitle">${context.description}</p>
      <a class="cta" href="#vision">Ver vision</a>
    </header>
  `;
}

export function FeatureCard(feature) {
  return `
    <article class="card">
      <h2>${feature.title}</h2>
      <p>${feature.body}</p>
    </article>
  `;
}

export function FootprintStats(footprint) {
  const avgEmployeesPerStore = Math.round(footprint.employees / footprint.stores);
  return `
    <section class="stats" aria-label="resumen de empresa">
      <p><strong>${footprint.stores}</strong> locales activos</p>
      <p><strong>${footprint.countries.length}</strong> paises de operacion</p>
      <p><strong>${avgEmployeesPerStore}</strong> empleados por local (aprox.)</p>
    </section>
  `;
}
