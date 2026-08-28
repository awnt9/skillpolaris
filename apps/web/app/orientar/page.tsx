import ResumeUploader from "@/components/ResumeUploader";

export default function OrientarPage() {
  return (
    <div className="flex flex-col items-center gap-4 py-8">
      <h1 className="text-3xl font-bold tracking-tight text-primary">Get oriented</h1>
      <p className="max-w-lg text-center text-secondary">
        Upload your resume as a PDF and we&apos;ll use it to guide you toward the roles that
        fit you best.
      </p>
      <ResumeUploader />
    </div>
  );
}
