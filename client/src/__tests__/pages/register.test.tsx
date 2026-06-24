import { describe, expect, it, mock, spyOn, afterEach } from "bun:test";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SignUp from "@/app/connection/register/page";

// ── Mocks ──────────────────────────────────────────────────────────────────

const mockPush = mock(() => {});

mock.module("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

// ── Helpers ────────────────────────────────────────────────────────────────

function fillForm(email: string, password: string, confirm: string) {
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: email } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
  fireEvent.change(screen.getByLabelText("Confirm Password"), { target: { value: confirm } });
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe("Register Page", () => {
  afterEach(() => {
    mockPush.mockClear();
  });

  // ── UI rendering ───────────────────────────────────────────────────────

  it("renders the welcome title", () => {
    render(<SignUp />);
    expect(screen.getByText("Welcome !")).toBeTruthy();
  });

  it("renders the subtitle", () => {
    render(<SignUp />);
    expect(screen.getByText("Create an account")).toBeTruthy();
  });

  it("renders email input", () => {
    render(<SignUp />);
    expect(screen.getByLabelText("Email")).toBeTruthy();
  });

  it("renders two password inputs", () => {
    render(<SignUp />);
    expect(screen.getByLabelText("Password")).toBeTruthy();
    expect(screen.getByLabelText("Confirm Password")).toBeTruthy();
  });

  it("renders sign up button", () => {
    render(<SignUp />);
    expect(screen.getByText("Sign Up")).toBeTruthy();
  });

  it("renders login link", () => {
    render(<SignUp />);
    expect(screen.getByText("Already have an account? Login")).toBeTruthy();
  });

  // ── Validation ─────────────────────────────────────────────────────────

  it("shows error when passwords do not match", async () => {
    render(<SignUp />);
    fillForm("test@example.com", "pass123", "pass456");
    fireEvent.click(screen.getByText("Sign Up"));

    await waitFor(() => {
      expect(screen.getByText("Passwords do not match")).toBeTruthy();
    });

    // Ensure redirect was NOT called
    expect(mockPush).not.toHaveBeenCalled();
  });

  // ── Successful signup ──────────────────────────────────────────────────

  it("redirects to login on successful signup (201)", async () => {
    const fetchSpy = spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({}), { status: 201 })
    );

    render(<SignUp />);
    fillForm("newuser@example.com", "secret123", "secret123");
    fireEvent.click(screen.getByText("Sign Up"));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/signup/"),
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: expect.stringContaining("newuser@example.com"),
        })
      );
      expect(mockPush).toHaveBeenCalledWith("/connection/login");
    });

    fetchSpy.mockRestore();
  });

  // ── API error ──────────────────────────────────────────────────────────

  it("displays backend error message on 400", async () => {
    const fetchSpy = spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ email: ["A user with this email already exists."] }), { status: 400 })
    );

    render(<SignUp />);
    fillForm("exists@example.com", "pass123", "pass123");
    fireEvent.click(screen.getByText("Sign Up"));

    await waitFor(() => {
      expect(screen.getByText("A user with this email already exists.")).toBeTruthy();
    });

    expect(mockPush).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  // ── Network error ──────────────────────────────────────────────────────

  it("displays generic error on network failure", async () => {
    const fetchSpy = spyOn(global, "fetch").mockRejectedValueOnce(new Error("Network failure"));

    render(<SignUp />);
    fillForm("fail@example.com", "pass123", "pass123");
    fireEvent.click(screen.getByText("Sign Up"));

    await waitFor(() => {
      expect(screen.getByText("An error occurred. Please try again later.")).toBeTruthy();
    });

    fetchSpy.mockRestore();
  });

  // ── Loading state ──────────────────────────────────────────────────────

  it("shows 'Creating account...' while loading", async () => {
    let resolvePromise!: (value: Response) => void;
    const fetchSpy = spyOn(global, "fetch").mockReturnValueOnce(
      new Promise<Response>((resolve) => { resolvePromise = resolve; })
    );

    render(<SignUp />);
    fillForm("loading@example.com", "pass123", "pass123");
    fireEvent.click(screen.getByText("Sign Up"));

    // Button text should change immediately
    expect(screen.getByText("Creating account...")).toBeTruthy();

    // Resolve to avoid hanging
    resolvePromise(new Response(JSON.stringify({}), { status: 201 }));
    fetchSpy.mockRestore();
  });

  it("disables submit button while loading", async () => {
    let resolvePromise!: (value: Response) => void;
    const fetchSpy = spyOn(global, "fetch").mockReturnValueOnce(
      new Promise<Response>((resolve) => { resolvePromise = resolve; })
    );

    render(<SignUp />);
    fillForm("disabled@example.com", "pass123", "pass123");
    fireEvent.click(screen.getByText("Sign Up"));

    const button = screen.getByRole("button") as HTMLButtonElement;
    expect(button.hasAttribute("disabled")).toBe(true);

    resolvePromise(new Response(JSON.stringify({}), { status: 201 }));
    fetchSpy.mockRestore();
  });
});