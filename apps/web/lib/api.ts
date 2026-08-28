export type Stats = {
  sources: number;
  records: number;
  positions: number;
};

const INTERNAL_API_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

export async function getStats(): Promise<Stats | null> {
  try {
    const res = await fetch(`${INTERNAL_API_URL}/stats`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as Stats;
  } catch {
    return null;
  }
}
