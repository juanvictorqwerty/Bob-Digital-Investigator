import { describe, expect, it } from "bun:test";
import {
  BackGroundColor,
  ForeGroundColor,
  BorderColor,
  ButtonColor,
  ButtonColorHover,
  ButtonTextColor,
} from "@/colors/Colors";

describe("Colors exports", () => {
  it("BackGroundColor is a string", () => {
    expect(typeof BackGroundColor).toBe("string");
    expect(BackGroundColor.length).toBeGreaterThan(0);
  });

  it("ForeGroundColor is a string", () => {
    expect(typeof ForeGroundColor).toBe("string");
    expect(ForeGroundColor.length).toBeGreaterThan(0);
  });

  it("BorderColor is a string", () => {
    expect(typeof BorderColor).toBe("string");
    expect(BorderColor.length).toBeGreaterThan(0);
  });

  it("ButtonColor is a string", () => {
    expect(typeof ButtonColor).toBe("string");
    expect(ButtonColor.length).toBeGreaterThan(0);
  });

  it("ButtonColorHover is a string", () => {
    expect(typeof ButtonColorHover).toBe("string");
    expect(ButtonColorHover.length).toBeGreaterThan(0);
  });

  it("ButtonTextColor is a string", () => {
    expect(typeof ButtonTextColor).toBe("string");
    expect(ButtonTextColor.length).toBeGreaterThan(0);
  });

  it("BackGroundColor contains a Tailwind utility class", () => {
    expect(BackGroundColor).toContain("bg-");
  });

  it("ButtonColor includes bg-blue", () => {
    expect(ButtonColor).toContain("bg-blue");
  });
});