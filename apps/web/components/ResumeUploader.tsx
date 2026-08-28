"use client";

import { useRef, useState } from "react";

const MAX_SIZE_BYTES = 10 * 1024 * 1024;
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type UploadState = "idle" | "ready" | "uploading" | "success" | "error";

export default function ResumeUploader() {
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<UploadState>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndSetFile = (candidate: File | undefined) => {
    if (!candidate) return;
    if (candidate.type !== "application/pdf") {
      setFile(null);
      setState("error");
      setMessage("Only PDF files are supported.");
      return;
    }
    if (candidate.size > MAX_SIZE_BYTES) {
      setFile(null);
      setState("error");
      setMessage("File exceeds the 10 MB limit.");
      return;
    }
    setFile(candidate);
    setState("ready");
    setMessage(null);
  };

  const handleUpload = async () => {
    if (!file) return;
    setState("uploading");
    setMessage(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_URL}/cv/upload`, { method: "POST", body: formData });
      if (!res.ok) {
        const body = (await res.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(body?.detail ?? "Upload failed.");
      }
      setState("success");
      setMessage("Resume received. Guidance is coming soon.");
    } catch (err) {
      setState("error");
      setMessage(err instanceof Error ? err.message : "Upload failed.");
    }
  };

  const reset = () => {
    setFile(null);
    setState("idle");
    setMessage(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="mx-auto w-full max-w-xl">
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          validateAndSetFile(event.dataTransfer.files[0]);
        }}
        onClick={() => inputRef.current?.click()}
        className={`clay flex cursor-pointer flex-col items-center gap-3 rounded-3xl px-8 py-14 text-center ${
          isDragging ? "clay-dropzone-active" : ""
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(event) => validateAndSetFile(event.target.files?.[0])}
        />
        {file ? (
          <>
            <p className="font-medium text-primary">{file.name}</p>
            <p className="text-sm text-secondary">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </>
        ) : (
          <>
            <p className="font-medium text-primary">Drag & drop your resume here</p>
            <p className="text-sm text-secondary">
              or click to browse — PDF only, up to 10 MB
            </p>
          </>
        )}
      </div>

      {message && (
        <p
          className={`mt-4 text-center text-sm font-medium ${
            state === "error" ? "text-red-400" : "text-primary"
          }`}
        >
          {message}
        </p>
      )}

      <div className="mt-6 flex justify-center gap-3">
        {file && state !== "uploading" && (
          <button
            onClick={reset}
            className="nav-link rounded-2xl px-5 py-2 text-sm font-medium"
          >
            Remove
          </button>
        )}
        <button
          onClick={handleUpload}
          disabled={!file || state === "uploading"}
          className="clay-button rounded-2xl px-6 py-2 text-sm font-semibold"
        >
          {state === "uploading" ? "Uploading…" : "Analyze resume"}
        </button>
      </div>
    </div>
  );
}
