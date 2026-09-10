import StatCard from "@/components/StatCard";
import { Carousel_003 } from "@/components/ui/skiper-ui/skiper49";
import { getStats } from "@/lib/api";

export const dynamic = "force-dynamic";

const taglines = [
  "Thousands of postings pulled in and kept up to date.",
  "Every tech job posting, structured and understood.",
  "From scattered listings to a clear picture of the market.",
  "Find your next role, backed by real data.",
  "The vocabulary the market actually uses, not a fixed list.",
];

export default async function HomePage() {
  const stats = await getStats();

  return (
    <div className="flex flex-col gap-16 py-8">
      <section className="relative text-center">
        <div className="relative inline-block">
          <div
            aria-hidden
            className="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-16 w-96 -translate-x-1/2 -translate-y-1/2 rounded-full opacity-40 blur-[80px]"
            style={{ backgroundColor: "#2D3FE7" }}
          />
          <h1 className="text-4xl font-bold tracking-tight text-primary sm:text-5xl">
            SkillPolaris
          </h1>
        </div>
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
            <StatCard
              key="postings"
              label="Postings collected"
              value={stats?.postings ?? null}
              tagline={taglines[0]}
            />,
            <StatCard
              key="sources"
              label="Sources tracked"
              value={stats?.sources ?? null}
              tagline={taglines[1]}
            />,
            <StatCard
              key="records"
              label="Job records"
              value={stats?.records ?? null}
              tagline={taglines[2]}
            />,
            <StatCard
              key="positions"
              label="Job positions"
              value={stats?.positions ?? null}
              tagline={taglines[3]}
            />,
            <StatCard
              key="skills"
              label="Skills tracked"
              value={stats?.skills ?? null}
              tagline={taglines[4]}
            />,
          ]}
        />
      </section>
    </div>
  );
}
