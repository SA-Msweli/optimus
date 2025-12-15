import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { LoginPage } from "./LoginPage";

// Mock Privy hooks
vi.mock("@privy-io/react-auth", () => ({
  useLoginWithEmail: vi.fn(),
}));

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

import { useLoginWithEmail } from "@privy-io/react-auth";

const renderLoginPage = () => {
  return render(
    <BrowserRouter>
      <LoginPage />
    </BrowserRouter>
  );
};

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
  });

  describe("Email Step", () => {
    it("should display email input and send code button on initial load", () => {
      renderLoginPage();

      expect(screen.getByText("Welcome Back")).toBeInTheDocument();
      expect(screen.getByLabelText("Email address")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /send code/i })).toBeInTheDocument();
    });

    it("should display email validation error when email is empty", async () => {
      const user = userEvent.setup();
      renderLoginPage();

      const sendButton = screen.getByRole("button", { name: /send code/i });
      await user.click(sendButton);

      expect(
        screen.getByText("Please enter your email address")
      ).toBeInTheDocument();
    });

    it("should display email validation error for invalid email format", async () => {
      const user = userEvent.setup();
      renderLoginPage();

      const emailInput = screen.getByLabelText("Email address");
      await user.type(emailInput, "invalid-email");

      const sendButton = screen.getByRole("button", { name: /send code/i });
      await user.click(sendButton);

      expect(
        screen.getByText("Please enter a valid email address")
      ).toBeInTheDocument();
    });

    it("should accept valid email format", async () => {
      const user = userEvent.setup();
      const mockSendCode = vi.fn().mockResolvedValue(undefined);
      vi.mocked(useLoginWithEmail).mockReturnValue({
        sendCode: mockSendCode,
        loginWithCode: vi.fn(),
      } as any);

      renderLoginPage();

      const emailInput = screen.getByLabelText("Email address");
      await user.type(emailInput, "test@example.com");

      const sendButton = screen.getByRole("button", { name: /send code/i });
      await user.click(sendButton);

      await waitFor(() => {
        expect(mockSendCode).toHaveBeenCalledWith({ email: "test@example.com" });
      });
    });

    it("should display loading state while sending code", async () => {
      const user = userEvent.setup();
      const mockSendCode = vi.fn(
        () =>
          new Promise((resolve) => {
            setTimeout(resolve, 100);
          })
      );
      vi.mocked(useLoginWithEmail).mockReturnValue({
        sendCode: mockSendCode,
        loginWithCode: vi.fn(),
      } as any);

      renderLoginPage();

      const emailInput = screen.getByLabelText("Email address");
      await user.type(emailInput, "test@example.com");

      const sendButton = screen.getByRole("button", { name: /send code/i });
      await user.click(sendButton);

      expect(screen.getByText("Sending code...")).toBeInTheDocument();
    });

    it("should display error message when sending code fails", async () => {
      const user = userEvent.setup();
      const mockSendCode = vi
        .fn()
        .mockRejectedValue(new Error("Network error"));
      vi.mocked(useLoginWithEmail).mockReturnValue({
        sendCode: mockSendCode,
        loginWithCode: vi.fn(),
      } as any);

      renderLoginPage();

      const emailInput = screen.getByLabelText("Email address");
      await user.type(emailInput, "test@example.com");

      const sendButton = screen.getByRole("button", { name: /send code/i });
      await user.click(sendButton);

      await waitFor(() => {
        expect(screen.getByText("Network error")).toBeInTheDocument();
      });
    });

    it("should transition to OTP step after successful code send", async () => {
      const user = userEvent.setup();
      const mockSendCode = vi.fn().mockResolvedValue(undefined);
      vi.mocked(useLoginWithEmail).mockReturnValue({
        sendCode: mockSendCode,
        loginWithCode: vi.fn(),
      } as any);

      renderLoginPage();

      const emailInput = screen.getByLabelText("Email address");
      await user.type(emailInput, "test@example.com");

      const sendButton = screen.getByRole("button", { name: /send code/i });
      await user.click(sendButton);

      await waitFor(() => {
        expect(screen.getByText("Verify Your Email")).toBeInTheDocument();
        expect(screen.getByLabelText("Verification code")).toBeInTheDocument();
      });
    });

    it("should clear email error when user starts typing", async () => {
      const user = userEvent.setup();
      renderLoginPage();

      const sendButton = screen.getByRole("button", { name: /send code/i });
      await user.click(sendButton);

      expect(
        screen.getByText("Please enter your email address")
      ).toBeInTheDocument();

      const emailInput = screen.getByLabelText("Email address");
      await user.type(emailInput, "test@example.com");

      expect(
        screen.queryByText("Please enter your email address")
      ).not.toBeInTheDocument();
    });
  });

  describe("OTP Step", () => {
    beforeEach(async () => {
      const user = userEvent.setup();
      const mockSendCode = vi.fn().mockResolvedValue(undefined);
      vi.mocked(useLoginWithEmail).mockReturnValue({
        sendCode: mockSendCode,
        loginWithCode: vi.fn(),
      } as any);

      renderLoginPage();

      const emailInput = screen.getByLabelText("Email address");
      await user.type(emailInput, "test@example.com");

      const sendButton = screen.getByRole("button", { name: /send code/i });
      await user.click(sendButton);

      await waitFor(() => {
        expect(screen.getByText("Verify Your Email")).toBeInTheDocument();
      });
    });

    it("should display OTP input and verify button", () => {
      expect(screen.getByLabelText("Verification code")).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /verify code/i })
      ).toBeInTheDocument();
    });

    it("should display error when OTP is empty", async () => {
      const user = userEvent.setup();

      const verifyButton = screen.getByRole("button", { name: /verify code/i });
      await user.click(verifyButton);

      expect(
        screen.getByText("Please enter the code from your email")
      ).toBeInTheDocument();
    });

    it("should display error when OTP is too short", async () => {
      const user = userEvent.setup();

      const codeInput = screen.getByLabelText("Verification code");
      await user.type(codeInput, "123");

      const verifyButton = screen.getByRole("button", { name: /verify code/i });
      await user.click(verifyButton);

      expect(
        screen.getByText("Code should be at least 6 characters")
      ).toBeInTheDocument();
    });

    it("should call loginWithCode with correct code", async () => {
      const user = userEvent.setup();
      const mockLoginWithCode = vi.fn().mockResolvedValue(undefined);
      vi.mocked(useLoginWithEmail).mockReturnValue({
        sendCode: vi.fn(),
        loginWithCode: mockLoginWithCode,
      } as any);

      const codeInput = screen.getByLabelText("Verification code");
      await user.type(codeInput, "123456");

      const verifyButton = screen.getByRole("button", { name: /verify code/i });
      await user.click(verifyButton);

      await waitFor(() => {
        expect(mockLoginWithCode).toHaveBeenCalledWith({ code: "123456" });
      });
    });

    it("should display loading state while verifying code", async () => {
      const user = userEvent.setup();
      const mockLoginWithCode = vi.fn(
        () =>
          new Promise((resolve) => {
            setTimeout(resolve, 100);
          })
      );
      vi.mocked(useLoginWithEmail).mockReturnValue({
        sendCode: vi.fn(),
        loginWithCode: mockLoginWithCode,
      } as any);

      const codeInput = screen.getByLabelText("Verification code");
      await user.type(codeInput, "123456");

      const verifyButton = screen.getByRole("button", { name: /verify code/i });
      await user.click(verifyButton);

      expect(screen.getByText("Verifying...")).toBeInTheDocument();
    });

    it("should display error message when verification fails", async () => {
      const user = userEvent.setup();
      const mockLoginWithCode = vi
        .fn()
        .mockRejectedValue(new Error("Invalid code"));
      vi.mocked(useLoginWithEmail).mockReturnValue({
        sendCode: vi.fn(),
        loginWithCode: mockLoginWithCode,
      } as any);

      const codeInput = screen.getByLabelText("Verification code");
      await user.type(codeInput, "123456");

      const verifyButton = screen.getByRole("button", { name: /verify code/i });
      await user.click(verifyButton);

      await waitFor(() => {
        expect(screen.getByText("Invalid code")).toBeInTheDocument();
      });
    });

    it("should redirect to dashboard on successful verification", async () => {
      const user = userEvent.setup();
      const mockLoginWithCode = vi.fn().mockResolvedValue(undefined);
      vi.mocked(useLoginWithEmail).mockReturnValue({
        sendCode: vi.fn(),
        loginWithCode: mockLoginWithCode,
      } as any);

      const codeInput = screen.getByLabelText("Verification code");
      await user.type(codeInput, "123456");

      const verifyButton = screen.getByRole("button", { name: /verify code/i });
      await user.click(verifyButton);

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith("/");
      });
    });

    it("should display back button to return to email step", () => {
      expect(
        screen.getByRole("button", { name: /back to email/i })
      ).toBeInTheDocument();
    });

    it("should return to email step when back button is clicked", async () => {
      const user = userEvent.setup();

      const backButton = screen.getByRole("button", { name: /back to email/i });
      await user.click(backButton);

      expect(screen.getByText("Welcome Back")).toBeInTheDocument();
      expect(screen.getByLabelText("Email address")).toBeInTheDocument();
    });

    it("should clear OTP error when user starts typing", async () => {
      const user = userEvent.setup();

      const verifyButton = screen.getByRole("button", { name: /verify code/i });
      await user.click(verifyButton);

      expect(
        screen.getByText("Please enter the code from your email")
      ).toBeInTheDocument();

      const codeInput = screen.getByLabelText("Verification code");
      await user.type(codeInput, "1");

      expect(
        screen.queryByText("Please enter the code from your email")
      ).not.toBeInTheDocument();
    });

    it("should convert code to uppercase", async () => {
      const user = userEvent.setup();
      const mockLoginWithCode = vi.fn().mockResolvedValue(undefined);
      vi.mocked(useLoginWithEmail).mockReturnValue({
        sendCode: vi.fn(),
        loginWithCode: mockLoginWithCode,
      } as any);

      const codeInput = screen.getByLabelText("Verification code");
      await user.type(codeInput, "abc123");

      const verifyButton = screen.getByRole("button", { name: /verify code/i });
      await user.click(verifyButton);

      await waitFor(() => {
        expect(mockLoginWithCode).toHaveBeenCalledWith({ code: "ABC123" });
      });
    });
  });

  describe("Accessibility", () => {
    it("should have proper labels for all inputs", () => {
      renderLoginPage();

      expect(screen.getByLabelText("Email address")).toBeInTheDocument();
    });

    it("should have aria-label for email input", () => {
      renderLoginPage();

      const emailInput = screen.getByLabelText("Email address");
      expect(emailInput).toHaveAttribute("aria-label", "Email address");
    });

    it("should have aria-label for OTP input after transition", async () => {
      const user = userEvent.setup();
      const mockSendCode = vi.fn().mockResolvedValue(undefined);
      vi.mocked(useLoginWithEmail).mockReturnValue({
        sendCode: mockSendCode,
        loginWithCode: vi.fn(),
      } as any);

      renderLoginPage();

      const emailInput = screen.getByLabelText("Email address");
      await user.type(emailInput, "test@example.com");

      const sendButton = screen.getByRole("button", { name: /send code/i });
      await user.click(sendButton);

      await waitFor(() => {
        const codeInput = screen.getByLabelText("Verification code");
        expect(codeInput).toHaveAttribute("aria-label", "Verification code");
      });
    });

    it("should disable inputs while loading", async () => {
      const user = userEvent.setup();
      const mockSendCode = vi.fn(
        () =>
          new Promise((resolve) => {
            setTimeout(resolve, 100);
          })
      );
      vi.mocked(useLoginWithEmail).mockReturnValue({
        sendCode: mockSendCode,
        loginWithCode: vi.fn(),
      } as any);

      renderLoginPage();

      const emailInput = screen.getByLabelText("Email address");
      await user.type(emailInput, "test@example.com");

      const sendButton = screen.getByRole("button", { name: /send code/i });
      await user.click(sendButton);

      expect(emailInput).toBeDisabled();
      expect(sendButton).toBeDisabled();
    });
  });

  describe("Form Submission", () => {
    it("should prevent default form submission", async () => {
      const user = userEvent.setup();
      renderLoginPage();

      const form = screen.getByLabelText("Email address").closest("form");
      const submitEvent = new Event("submit", { bubbles: true });
      const preventDefaultSpy = vi.spyOn(submitEvent, "preventDefault");

      form?.dispatchEvent(submitEvent);

      expect(preventDefaultSpy).toHaveBeenCalled();
    });
  });

  describe("Email Validation", () => {
    it("should accept various valid email formats", async () => {
      const user = userEvent.setup();
      const mockSendCode = vi.fn().mockResolvedValue(undefined);
      vi.mocked(useLoginWithEmail).mockReturnValue({
        sendCode: mockSendCode,
        loginWithCode: vi.fn(),
      } as any);

      const validEmails = [
        "user@example.com",
        "user.name@example.com",
        "user+tag@example.co.uk",
        "user123@test-domain.com",
      ];

      for (const validEmail of validEmails) {
        vi.clearAllMocks();
        mockSendCode.mockResolvedValue(undefined);

        const { unmount } = renderLoginPage();

        const emailInput = screen.getByLabelText("Email address");
        await user.clear(emailInput);
        await user.type(emailInput, validEmail);

        const sendButton = screen.getByRole("button", { name: /send code/i });
        await user.click(sendButton);

        await waitFor(() => {
          expect(mockSendCode).toHaveBeenCalledWith({ email: validEmail });
        });

        unmount();
      }
    });

    it("should reject invalid email formats", async () => {
      const user = userEvent.setup();
      renderLoginPage();

      const invalidEmails = [
        "notanemail",
        "user@",
        "@example.com",
        "user @example.com",
        "user@example",
      ];

      for (const invalidEmail of invalidEmails) {
        const emailInput = screen.getByLabelText("Email address");
        await user.clear(emailInput);
        await user.type(emailInput, invalidEmail);

        const sendButton = screen.getByRole("button", { name: /send code/i });
        await user.click(sendButton);

        expect(
          screen.getByText("Please enter a valid email address")
        ).toBeInTheDocument();

        // Clear for next iteration
        await user.clear(emailInput);
      }
    });
  });
});
