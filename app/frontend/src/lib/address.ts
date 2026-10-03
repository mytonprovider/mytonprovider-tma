import type { Explorer } from "@/stores/settings";

export const ADDRESS_RE = /^[A-Za-z0-9_+/-]{48}$/;

export const RAW_RE = /^(0|-1):([0-9a-fA-F]{64})$/;
const TAG = 0x51;

function base64Decode(value: string): Uint8Array {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(normalized);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

function base64UrlEncode(bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_");
}

function crc16(bytes: Uint8Array): number {
  let crc = 0;
  for (let i = 0; i < bytes.length; i++) {
    crc ^= bytes[i] << 8;
    for (let j = 0; j < 8; j++) {
      crc = crc & 0x8000 ? (crc << 1) ^ 0x1021 : crc << 1;
      crc &= 0xffff;
    }
  }
  return crc;
}

function sealed(bytes: Uint8Array): string {
  const crc = crc16(bytes.slice(0, 34));
  bytes[34] = (crc >> 8) & 0xff;
  bytes[35] = crc & 0xff;
  return base64UrlEncode(bytes);
}

function fromRaw(workchain: string, hash: string): string {
  const bytes = new Uint8Array(36);
  bytes[0] = TAG;
  bytes[1] = Number(workchain) & 0xff;
  for (let i = 0; i < 32; i++) bytes[i + 2] = parseInt(hash.slice(i * 2, i * 2 + 2), 16);
  return sealed(bytes);
}

export function parseAddress(value: string): string | null {
  const raw = RAW_RE.exec(value);
  if (raw) return fromRaw(raw[1], raw[2]);
  if (!ADDRESS_RE.test(value)) return null;
  try {
    const bytes = base64Decode(value);
    if (bytes.length !== 36 || crc16(bytes.slice(0, 34)) !== (bytes[34] << 8) + bytes[35]) return null;
    bytes[0] = (bytes[0] & 0x80) | TAG;
    return sealed(bytes);
  } catch {
    return null;
  }
}

export function toUserFriendly(address: string): string {
  return parseAddress(address) ?? address.replace(/^EQ/, "UQ");
}

export function explorerAddressUrl(address: string, explorer: Explorer): string {
  return explorer === "tonscan" ? `https://tonscan.org/address/${address}` : `https://tonviewer.com/${address}`;
}
