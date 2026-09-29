import { companyContext } from "./data.js";
import { Hero, FeatureCard, FootprintStats } from "./components.js";
import { mountApp } from "../shared/dom.js";

mountApp("#app", () => `
    ${Hero(companyContext)}
    ${FootprintStats(companyContext.footprint)}
    <main id="vision" class="grid">
      ${companyContext.features.map((feature) => FeatureCard(feature)).join("")}
    </main>
  `);
