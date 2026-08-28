import { companyContext } from "./data.js";
import { Hero, FeatureCard, FootprintStats } from "./components.js";

const app = document.querySelector("#app");

if (app) {
  app.innerHTML = `
    ${Hero(companyContext)}
    ${FootprintStats(companyContext.footprint)}
    <main id="vision" class="grid">
      ${companyContext.features.map((feature) => FeatureCard(feature)).join("")}
    </main>
  `;
}
