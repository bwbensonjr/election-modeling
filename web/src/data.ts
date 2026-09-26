import type { ComponentAsset, Manifest, RaceAsset } from "./types";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

export function validateManifest(value: unknown): Manifest {
  assert(typeof value === "object" && value !== null, "manifest must be an object");
  const manifest = value as Manifest;
  assert(manifest.schema_version === 1, `unsupported bundle schema ${manifest.schema_version}`);
  assert(Number.isInteger(manifest.draw_count) && manifest.draw_count > 0, "invalid draw count");
  assert(Array.isArray(manifest.races) && manifest.races.length > 0, "manifest has no races");
  const ids = manifest.races.map((race) => race.target_id);
  assert(ids.every(Boolean) && new Set(ids).size === ids.length, "manifest has missing or duplicate targets");
  assert(typeof manifest.components === "object" && manifest.components !== null, "manifest has no components");
  for (const race of manifest.races) {
    assert(Boolean(manifest.components[race.component]), `${race.target_id}: missing component ${race.component}`);
    assert(Boolean(manifest.assets[race.asset]), `${race.target_id}: missing race asset digest`);
  }
  return manifest;
}

async function digest(bytes: ArrayBuffer): Promise<string> {
  const result = await crypto.subtle.digest("SHA-256", bytes);
  const hex = [...new Uint8Array(result)].map((value) => value.toString(16).padStart(2, "0")).join("");
  return `sha256:${hex}`;
}

export class BundleClient {
  private componentCache = new Map<string, Promise<ComponentAsset>>();

  constructor(private readonly baseUrl: string, private readonly manifest: Manifest) {}

  static async load(baseUrl: string): Promise<BundleClient> {
    const response = await fetch(`${baseUrl}/manifest.json`);
    if (!response.ok) throw new Error(`failed to load forecast manifest: ${response.status}`);
    return new BundleClient(baseUrl, validateManifest(await response.json()));
  }

  getManifest(): Manifest {
    return this.manifest;
  }

  async loadRace(targetId: string): Promise<RaceAsset> {
    const race = this.manifest.races.find((candidate) => candidate.target_id === targetId);
    if (!race) throw new Error(`unknown target ${targetId}`);
    const asset = await this.loadAsset<RaceAsset>(race.asset);
    assert(asset.schema_version === 1, `${race.asset}: unsupported schema`);
    assert(asset.target_id === targetId, `${race.asset}: target identity mismatch`);
    assert(asset.draws.length === this.manifest.draw_count, `${race.asset}: inconsistent draw count`);
    return asset;
  }

  loadComponent(name: string): Promise<ComponentAsset> {
    const existing = this.componentCache.get(name);
    if (existing) return existing;
    const metadata = this.manifest.components[name];
    if (!metadata) return Promise.reject(new Error(`unknown component ${name}`));
    const promise = this.loadAsset<ComponentAsset>(metadata.asset).then((asset) => {
      assert(asset.schema_version === 1, `${metadata.asset}: unsupported schema`);
      assert(asset.component === name, `${metadata.asset}: component identity mismatch`);
      for (const term of metadata.scenario_terms) {
        assert(Array.isArray(asset.terms[term]), `${metadata.asset}: missing term ${term}`);
        assert(asset.terms[term].length === this.manifest.draw_count, `${metadata.asset}: inconsistent ${term} draws`);
      }
      return asset;
    });
    this.componentCache.set(name, promise);
    return promise;
  }

  private async loadAsset<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}/${path}`);
    if (!response.ok) throw new Error(`failed to load ${path}: ${response.status}`);
    const bytes = await response.arrayBuffer();
    const actual = await digest(bytes);
    assert(actual === this.manifest.assets[path], `${path}: digest mismatch`);
    return JSON.parse(new TextDecoder().decode(bytes)) as T;
  }
}
