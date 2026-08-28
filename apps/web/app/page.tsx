import StatCard from "@/components/StatCard";
import { Carousel_003 } from "@/components/ui/skiper-ui/skiper49";
import { getStats } from "@/lib/api";

export const dynamic = "force-dynamic";

const taglines = [
  "Every tech job posting, structured and understood.",
  "From scattered listings to a clear picture of the market.",
  "Find your next role, backed by real data.",
];

function EmptyStatCard() {
  return (
    <div className="clay flex h-full w-full flex-col items-center justify-center gap-3 rounded-3xl px-8 py-6 text-center opacity-40">
      <p className="text-2xl font-bold text-secondary">···</p>
      <p className="text-sm font-medium text-secondary">More stats coming soon</p>
    </div>
  );
}

export default async function HomePage() {
  const stats = await getStats();

  return (
    <div className="flex flex-col gap-16 py-8">
      <section className="relative text-center">
        <div
          aria-hidden
          className="pointer-events-none absolute left-1/2 top-10 -z-10 h-48 w-[32rem] -translate-x-1/2 rounded-full opacity-25 blur-[100px]"
          style={{ backgroundColor: "#DFF7FF" }}
        />
        <h1 className="text-4xl font-bold tracking-tight text-primary sm:text-5xl">
          SkillPolaris
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-secondary">
          Empowering career decision-making.
        </p>
      </section>

      <section>
        <Carousel_003
          showPagination
          loop={false}
          perView={3}
          initialSlide={2}
          slides={[
            <EmptyStatCard key="pad-start" />,
            <StatCard
              key="sources"
              label="Sources tracked"
              value={stats?.sources ?? null}
              tagline={taglines[0]}
            />,
            <StatCard
              key="records"
              label="Job records"
              value={stats?.records ?? null}
              tagline={taglines[1]}
            />,
            <StatCard
              key="positions"
              label="Job positions"
              value={stats?.positions ?? null}
              tagline={taglines[2]}
            />,
            <EmptyStatCard key="pad-end" />,
          ]}
        />
      </section>
    </div>
  );
}
