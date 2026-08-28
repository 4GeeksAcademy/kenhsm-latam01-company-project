import { operationalSnapshot } from "./data.js";
import { Sidebar, DashboardHeader, KpiCard, ContextFact } from "./components.js";

const app = document.querySelector("#app");

if (app) {
  app.innerHTML = `
    <div class="layout">
      ${Sidebar()}
      <main class="content">
        ${DashboardHeader(operationalSnapshot.dateLabel)}
        <section class="cards">
          ${operationalSnapshot.metrics.map((metric) => KpiCard(metric)).join("")}
        </section>
        ${ContextFact(operationalSnapshot.contextFact)}
      </main>
    </div>
  `;
}
