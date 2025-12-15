import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useLoginWithEmail } from "@privy-io/react-auth";
import { Mail, Lock, Loader2, AlertCircle, CheckCircle } from "lucide-react";

type LoginStep = "email" | "otp";

interface LoginError {
  type: "email" | "otp" | "general";
  message: string;
}

export function LoginPage() {
  const navigate = useNavigate();
  const { sendCode, loginWithCode } = useLoginWithEmail();

  const [step, setStep] = useState<LoginStep>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<LoginError | null>(null);
  const [codeSent, setCodeSent] = useState(false);

  // Email validation
  const isValidEmail = (emailValue: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(emailValue);
  };

  // Handle sending OTP
  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate email
    if (!email.trim()) {
      setError({
        type: "email",
        message: "Please enter your email address",
      });
      return;
    }

    if (!isValidEmail(email)) {
      setError({
        type: "email",
        message: "Please enter a valid email address",
      });
      return;
    }

    setIsLoading(true);

    try {
      await sendCode({ email });
      setCodeSent(true);
      setStep("otp");
    } catch (err) {
      setError({
        type: "email",
        message:
          err instanceof Error
            ? err.message
            : "Failed to send code. Please try again.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Handle OTP verification
  const handleLoginWithCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate OTP
    if (!code.trim()) {
      setError({
        type: "otp",
        message: "Please enter the code from your email",
      });
      return;
    }

    if (code.length < 6) {
      setError({
        type: "otp",
        message: "Code should be at least 6 characters",
      });
      return;
    }

    setIsLoading(true);

    try {
      await loginWithCode({ code });
      // Redirect to dashboard on successful login
      navigate("/");
    } catch (err) {
      setError({
        type: "otp",
        message:
          err instanceof Error
            ? err.message
            : "Invalid code. Please try again.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Handle going back to email step
  const handleBackToEmail = () => {
    setStep("email");
    setCode("");
    setCodeSent(false);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        {/* Logo/Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600 mb-2">
            Optimus
          </h1>
          <p className="text-gray-600">Your Gateway to DeFi Banking</p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          {step === "email" ? (
            <>
              {/* Email Step */}
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Welcome Back
              </h2>
              <p className="text-gray-600 mb-6">
                Sign in with your email to access your account
              </p>

              <form onSubmit={handleSendCode} className="space-y-4">
                {/* Email Input */}
                <div>
                  <label
                    htmlFor="email"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Email Address
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                    <input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value);
                        if (error?.type === "email") {
                          setError(null);
                        }
                      }}
                      placeholder="you@example.com"
                      className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                      disabled={isLoading}
                      aria-label="Email address"
                    />
                  </div>
                </div>

                {/* Email Error */}
                {error?.type === "email" && (
                  <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-red-700">{error.message}</p>
                  </div>
                )}

                {/* Send Code Button */}
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold py-2 px-4 rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      Sending code...
                    </>
                  ) : (
                    <>
                      <Mail className="h-5 w-5" />
                      Send Code
                    </>
                  )}
                </button>
              </form>

              {/* Info Text */}
              <p className="text-center text-sm text-gray-600 mt-6">
                We'll send a one-time code to your email address
              </p>
            </>
          ) : (
            <>
              {/* OTP Step */}
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Verify Your Email
              </h2>
              <p className="text-gray-600 mb-6">
                Enter the code we sent to{" "}
                <span className="font-semibold text-gray-900">{email}</span>
              </p>

              <form onSubmit={handleLoginWithCode} className="space-y-4">
                {/* OTP Input */}
                <div>
                  <label
                    htmlFor="code"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Verification Code
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                    <input
                      id="code"
                      type="text"
                      value={code}
                      onChange={(e) => {
                        setCode(e.target.value.toUpperCase());
                        if (error?.type === "otp") {
                          setError(null);
                        }
                      }}
                      placeholder="Enter 6-digit code"
                      maxLength={10}
                      className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition font-mono text-lg tracking-widest"
                      disabled={isLoading}
                      aria-label="Verification code"
                    />
                  </div>
                </div>

                {/* OTP Error */}
                {error?.type === "otp" && (
                  <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-red-700">{error.message}</p>
                  </div>
                )}

                {/* Verify Button */}
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold py-2 px-4 rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="h-5 w-5" />
                      Verify Code
                    </>
                  )}
                </button>

                {/* Back Button */}
                <button
                  type="button"
                  onClick={handleBackToEmail}
                  disabled={isLoading}
                  className="w-full bg-gray-100 text-gray-700 font-semibold py-2 px-4 rounded-lg hover:bg-gray-200 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Back to Email
                </button>
              </form>

              {/* Info Text */}
              <p className="text-center text-sm text-gray-600 mt-6">
                Didn't receive the code? Check your spam folder or try again.
              </p>
            </>
          )}

          {/* General Error */}
          {error?.type === "general" && (
            <div className="mt-6 flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
              <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{error.message}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <p className="text-center text-sm text-gray-600 mt-6">
          By signing in, you agree to our Terms of Service and Privacy Policy
        </p>
      </div>
    </div>
  );
}
