import { cp, mkdir, rm } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { FORECAST } from "./forecast.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const source = path.resolve(here, `../../data/forecast/2026/interactive/${FORECAST}`);
const destination = path.resolve(here, `../public/data/2026/${FORECAST}`);

await rm(destination, { recursive: true, force: true });
await mkdir(path.dirname(destination), { recursive: true });
await cp(source, destination, { recursive: true });
