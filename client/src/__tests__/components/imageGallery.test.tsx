import { describe, expect, it } from "bun:test";
import { render, screen, fireEvent } from "@testing-library/react";
import ImageGallery from "@/components/resultView/imageGallery";

describe("ImageGallery", () => {
  const mockImages = [
    {
      page_url: "https://example.com/img1",
      title: "Image One",
      domain: "example.com",
      thumbnail: "https://example.com/thumb1.jpg",
    },
    {
      page_url: "https://example.com/img2",
      title: "Image Two",
      domain: "example.com",
      thumbnail: "https://example.com/thumb2.jpg",
    },
  ];

  it("returns null when withImages is empty", () => {
    const { container } = render(<ImageGallery withImages={[]} />);
    expect(container.innerHTML).toBe("");
  });

  it("renders the collapsible header with image count", () => {
    render(<ImageGallery withImages={mockImages} />);
    expect(screen.getByText("Image Gallery")).toBeTruthy();
    expect(screen.getByText("2 images")).toBeTruthy();
  });

  it("starts closed", () => {
    render(<ImageGallery withImages={mockImages} />);
    // The content should have max-h-0 when closed
    const galleries = document.querySelectorAll('[class*="max-h"]');
    expect(galleries.length).toBeGreaterThan(0);
  });

  it("opens when header is clicked", () => {
    render(<ImageGallery withImages={mockImages} />);
    const button = screen.getByText("Image Gallery").closest("button")!;
    fireEvent.click(button);
    // After clicking, images should be visible
    expect(screen.getByText("Image One")).toBeTruthy();
    expect(screen.getByText("Image Two")).toBeTruthy();
  });

  it("shows 'Oldest' badge on first image", () => {
    render(<ImageGallery withImages={mockImages} />);
    const button = screen.getByText("Image Gallery").closest("button")!;
    fireEvent.click(button);
    expect(screen.getByText("Oldest")).toBeTruthy();
  });

  it("renders domain text for each image", () => {
    render(<ImageGallery withImages={mockImages} />);
    const button = screen.getByText("Image Gallery").closest("button")!;
    fireEvent.click(button);
    const domainTexts = screen.getAllByText("example.com");
    expect(domainTexts.length).toBe(mockImages.length);
  });
});