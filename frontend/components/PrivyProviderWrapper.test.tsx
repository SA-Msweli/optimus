import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { PrivyProviderWrapper } from "./PrivyProviderWrapper";

// Mock the Privy provider
vi.mock("@privy-io/react-auth", () => ({
  PrivyProvider: ({ children, appId, clientId, config }: any) => {
    // Verify that required props are passed
    if (!appId || !clientId) {
      throw new Error("Missing Privy configuration");
    }
    return <div data-testid="privy-provider">{children}</div>;
  },
}));

// Mock the chains
vi.mock("@/config/chains", () => ({
  movementMainnet: {
    id: 126,
    name: "Movement Mainnet",
  },
  movementTestnet: {
    id: 250,
    name: "Movement Testnet",
  },
}));

describe("PrivyProviderWrapper", () => {
  beforeEach(() => {
    // Set up environment variables
    import.meta.env.VITE_PRIVY_APP_ID = "test-app-id";
    import.meta.env.VITE_PRIVY_CLIENT_ID = "test-client-id";
  });

  it("should render children when properly configured", () => {
    render(
      <PrivyProviderWrapper>
        <div data-testid="test-child">Test Content</div>
      </PrivyProviderWrapper>
    );

    expect(screen.getByTestId("test-child")).toBeDefined();
    expect(screen.getByText("Test Content")).toBeDefined();
  });

  it("should render PrivyProvider component", () => {
    render(
      <PrivyProviderWrapper>
        <div>Test</div>
      </PrivyProviderWrapper>
    );

    expect(screen.getByTestId("privy-provider")).toBeDefined();
  });

  it("should throw error when VITE_PRIVY_APP_ID is missing", () => {
    import.meta.env.VITE_PRIVY_APP_ID = "";
    import.meta.env.VITE_PRIVY_CLIENT_ID = "test-client-id";

    expect(() => {
      render(
        <PrivyProviderWrapper>
          <div>Test</div>
        </PrivyProviderWrapper>
      );
    }).toThrow("Missing Privy configuration");
  });

  it("should throw error when VITE_PRIVY_CLIENT_ID is missing", () => {
    import.meta.env.VITE_PRIVY_APP_ID = "test-app-id";
    import.meta.env.VITE_PRIVY_CLIENT_ID = "";

    expect(() => {
      render(
        <PrivyProviderWrapper>
          <div>Test</div>
        </PrivyProviderWrapper>
      );
    }).toThrow("Missing Privy configuration");
  });

  it("should throw error when both Privy environment variables are missing", () => {
    import.meta.env.VITE_PRIVY_APP_ID = "";
    import.meta.env.VITE_PRIVY_CLIENT_ID = "";

    expect(() => {
      render(
        <PrivyProviderWrapper>
          <div>Test</div>
        </PrivyProviderWrapper>
      );
    }).toThrow("Missing Privy configuration");
  });

  it("should include error message mentioning environment variables", () => {
    import.meta.env.VITE_PRIVY_APP_ID = "";
    import.meta.env.VITE_PRIVY_CLIENT_ID = "";

    expect(() => {
      render(
        <PrivyProviderWrapper>
          <div>Test</div>
        </PrivyProviderWrapper>
      );
    }).toThrow(/VITE_PRIVY_APP_ID|VITE_PRIVY_CLIENT_ID/);
  });
});
