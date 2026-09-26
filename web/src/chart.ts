import { bin, extent, max } from "d3-array";
import { scaleLinear } from "d3-scale";
import { curveBasis, line } from "d3-shape";

const SVG_NS = "http://www.w3.org/2000/svg";

function element<K extends keyof SVGElementTagNameMap>(name: K): SVGElementTagNameMap[K] {
  return document.createElementNS(SVG_NS, name);
}

export function renderDistribution(
  container: HTMLElement,
  published: number[],
  scenario: number[],
): void {
  container.replaceChildren();
  const width = Math.max(container.clientWidth || 720, 320);
  const height = width < 520 ? 250 : 310;
  const margin = { top: 14, right: 18, bottom: 34, left: 18 };
  const combined = [...published, ...scenario, 0];
  const [rawMin = -1, rawMax = 1] = extent(combined);
  const padding = Math.max((rawMax - rawMin) * 0.08, 2);
  const domain: [number, number] = [rawMin - padding, rawMax + padding];
  const bins = bin().domain(domain).thresholds(38);
  const publishedBins = bins(published);
  const scenarioBins = bins(scenario);
  const yMaximum = max([...publishedBins, ...scenarioBins], (value) => value.length) || 1;
  const x = scaleLinear().domain(domain).range([margin.left, width - margin.right]);
  const y = scaleLinear().domain([0, yMaximum]).range([height - margin.bottom, margin.top]);
  const makeLine = line<(typeof publishedBins)[number]>()
    .x((value) => x(((value.x0 || 0) + (value.x1 || 0)) / 2))
    .y((value) => y(value.length))
    .curve(curveBasis);

  const svg = element("svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("aria-hidden", "true");
  svg.classList.add("distribution-chart");

  const baseline = element("line");
  baseline.setAttribute("x1", String(margin.left));
  baseline.setAttribute("x2", String(width - margin.right));
  baseline.setAttribute("y1", String(height - margin.bottom));
  baseline.setAttribute("y2", String(height - margin.bottom));
  baseline.classList.add("axis-line");
  svg.append(baseline);

  const zero = element("line");
  zero.setAttribute("x1", String(x(0)));
  zero.setAttribute("x2", String(x(0)));
  zero.setAttribute("y1", String(margin.top));
  zero.setAttribute("y2", String(height - margin.bottom));
  zero.classList.add("zero-line");
  svg.append(zero);

  const zeroLabel = element("text");
  zeroLabel.setAttribute("x", String(x(0) + 5));
  zeroLabel.setAttribute("y", String(margin.top + 12));
  zeroLabel.textContent = "0";
  zeroLabel.classList.add("zero-label");
  svg.append(zeroLabel);

  for (const [name, values] of [["published", publishedBins], ["scenario", scenarioBins]] as const) {
    const path = element("path");
    path.setAttribute("d", makeLine(values) || "");
    path.classList.add("density-line", `density-line--${name}`);
    svg.append(path);
  }

  for (const tick of x.ticks(width < 520 ? 5 : 8)) {
    const text = element("text");
    text.setAttribute("x", String(x(tick)));
    text.setAttribute("y", String(height - 10));
    text.setAttribute("text-anchor", "middle");
    text.classList.add("tick-label");
    text.textContent = `${tick > 0 ? "+" : ""}${tick.toFixed(0)}`;
    svg.append(text);
  }
  container.append(svg);
}
