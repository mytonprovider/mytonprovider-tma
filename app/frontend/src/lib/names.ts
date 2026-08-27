export const NAME_MAX = 32;

export function cleanName(value: string): string {
  return value.split(/\s+/).filter(Boolean).join(" ").slice(0, NAME_MAX).trim();
}
