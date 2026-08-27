import { adaptProvider } from "./adapt";
import type { SearchRequest, SearchResponse } from "./dto";
import { http } from "./http";
import type { Provider } from "./types";

const CATALOG_LIMIT = 1000;

export async function fetchCatalog(): Promise<Provider[]> {
  const body: SearchRequest = { filters: {}, exact: [], limit: CATALOG_LIMIT, offset: 0 };
  const { providers } = await http.post<SearchResponse>("/api/v1/providers/search", body);
  const nowSec = Math.floor(Date.now() / 1000);
  return providers.map((dto) => adaptProvider(dto, nowSec));
}
