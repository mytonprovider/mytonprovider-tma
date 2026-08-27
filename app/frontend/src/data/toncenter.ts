const TONCENTER_BASE = "https://toncenter.com/api/v3";

interface StackItem {
  type: string;
  value: string | StackItem[];
}

interface RunGetMethodResult {
  exit_code: number;
  stack: StackItem[];
}

const MIN_GAP_MS = 1250;
const MAX_RETRIES = 3;
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

let lastAt = 0;
let queue: Promise<unknown> = Promise.resolve();

function throttle<T>(task: () => Promise<T>): Promise<T> {
  const result = queue.then(async () => {
    const wait = lastAt + MIN_GAP_MS - Date.now();
    if (wait > 0) await delay(wait);
    lastAt = Date.now();
    return task();
  });
  queue = result.then(
    () => undefined,
    () => undefined,
  );
  return result;
}

async function runGetMethod(address: string, method: string): Promise<RunGetMethodResult> {
  return throttle(async () => {
    for (let attempt = 0; ; attempt++) {
      const response = await fetch(`${TONCENTER_BASE}/runGetMethod`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address, method, stack: [] }),
      });
      if (response.status === 429 && attempt < MAX_RETRIES) {
        await delay(MIN_GAP_MS);
        continue;
      }
      if (!response.ok) {
        throw new Error(`toncenter ${method} failed with ${response.status}`);
      }
      return (await response.json()) as RunGetMethodResult;
    }
  });
}

const num = (item: StackItem): number => Number(BigInt(item.value as string));
const hex64 = (item: StackItem): string => BigInt(item.value as string).toString(16).padStart(64, "0");

export interface StorageContractProvider {
  pubkey: string;
  maxSpan: number;
  lastProof: number;
}

export interface StorageContract {
  bagId: string;
  fileSize: number;
  chunkSize: number;
  merkleHash: string;
  balance: number;
  providers: StorageContractProvider[];
}

export async function readStorageContract(address: string): Promise<StorageContract | null> {
  const info = await runGetMethod(address, "get_storage_info");
  if (info.exit_code !== 0) return null;
  const contract = await runGetMethod(address, "get_providers");
  if (contract.exit_code !== 0) return null;

  const tuple = contract.stack[0].value as StackItem[];
  const providers = tuple.map((entry): StorageContractProvider => {
    const row = entry.value as StackItem[];
    return {
      pubkey: hex64(row[0]),
      maxSpan: num(row[2]),
      lastProof: num(row[3]),
    };
  });

  return {
    bagId: hex64(info.stack[0]),
    fileSize: num(info.stack[1]),
    chunkSize: num(info.stack[2]),
    merkleHash: hex64(info.stack[4]),
    balance: num(contract.stack[1]),
    providers,
  };
}
