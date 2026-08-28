type StatCardProps = {
  label: string;
  value: number | null;
  tagline: string;
};

export default function StatCard({ label, value, tagline }: StatCardProps) {
  return (
    <div className="clay flex h-full w-full flex-col items-center justify-center gap-3 rounded-3xl px-8 py-6 text-center">
      <div>
        <p className="text-4xl font-bold text-accent">
          {value === null ? "—" : value.toLocaleString("en-US")}
        </p>
        <p className="mt-2 text-sm font-medium text-secondary">{label}</p>
      </div>
      <p className="text-sm font-medium text-primary">{tagline}</p>
    </div>
  );
}
