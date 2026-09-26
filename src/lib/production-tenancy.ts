/** Browser convenience state; backend membership checks remain authoritative. */
const STORAGE_KEY = "hakiscribe.production-tenancy";

export interface ProductionTenancyContext {
  organisationId: string;
  workspaceId: string;
}

export function loadProductionTenancy(): ProductionTenancyContext | null {
  if (typeof window === "undefined") return null;
  try {
    const value = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "null") as Partial<ProductionTenancyContext> | null;
    return value?.organisationId && value.workspaceId ? { organisationId: value.organisationId, workspaceId: value.workspaceId } : null;
  } catch {
    return null;
  }
}

export function saveProductionTenancy(value: ProductionTenancyContext | null): void {
  if (typeof window === "undefined") return;
  if (!value) window.localStorage.removeItem(STORAGE_KEY);
  else window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
}
