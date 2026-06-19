import { describe, expect, it } from "bun:test";
import { render, screen } from "@testing-library/react";
import UploadCard from "@/components/UploadCard";

describe("UploadCard", () => {
  it("renders the dropzone initially", () => {
    render(<UploadCard onFileSelect={() => {}} />);
    expect(screen.getByText("Upload Media")).toBeTruthy();
    expect(screen.getByText("Select a file to investigate")).toBeTruthy();
    expect(screen.getByText("Click to browse or drop file here")).toBeTruthy();
  });

  it("renders the file constraints text", () => {
    render(<UploadCard onFileSelect={() => {}} />);
    expect(screen.getByText(/Images or Videos up to 20s/)).toBeTruthy();
  });

  it("accepts image/* and video/* file types", () => {
    render(<UploadCard onFileSelect={() => {}} />);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).toBeTruthy();
    expect(fileInput.accept).toContain("image/*");
    expect(fileInput.accept).toContain("video/*");
  });
});
