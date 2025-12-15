import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { movementMainnet, movementTestnet } from "./chains";

describe("Movement Network Chain Configuration", () => {
  describe("movementMainnet", () => {
    it("should have correct chain ID", () => {
      expect(movementMainnet.id).toBe(126);
    });

    it("should have correct name", () => {
      expect(movementMainnet.name).toBe("Movement Mainnet");
    });

    it("should have correct network identifier", () => {
      expect(movementMainnet.network).toBe("movement-mainnet");
    });

    it("should have MOVE as native currency", () => {
      expect(movementMainnet.nativeCurrency.symbol).toBe("MOVE");
      expect(movementMainnet.nativeCurrency.name).toBe("MOVE");
      expect(movementMainnet.nativeCurrency.decimals).toBe(8);
    });

    it("should have valid RPC URL", () => {
      const rpcUrl = movementMainnet.rpcUrls.default.http[0];
      expect(rpcUrl).toBeDefined();
      expect(typeof rpcUrl).toBe("string");
      expect(rpcUrl.length).toBeGreaterThan(0);
    });

    it("should have valid block explorer", () => {
      const explorer = movementMainnet.blockExplorers?.default;
      expect(explorer).toBeDefined();
      expect(explorer?.name).toBe("Movement Explorer");
      expect(explorer?.url).toContain("explorer.movementnetwork.xyz");
    });

    it("should not be marked as testnet", () => {
      expect(movementMainnet.testnet).toBeUndefined();
    });
  });

  describe("movementTestnet", () => {
    it("should have correct chain ID", () => {
      expect(movementTestnet.id).toBe(250);
    });

    it("should have correct name", () => {
      expect(movementTestnet.name).toBe("Movement Testnet");
    });

    it("should have correct network identifier", () => {
      expect(movementTestnet.network).toBe("movement-testnet");
    });

    it("should have MOVE as native currency", () => {
      expect(movementTestnet.nativeCurrency.symbol).toBe("MOVE");
      expect(movementTestnet.nativeCurrency.name).toBe("MOVE");
      expect(movementTestnet.nativeCurrency.decimals).toBe(8);
    });

    it("should have valid RPC URL", () => {
      const rpcUrl = movementTestnet.rpcUrls.default.http[0];
      expect(rpcUrl).toBeDefined();
      expect(typeof rpcUrl).toBe("string");
      expect(rpcUrl.length).toBeGreaterThan(0);
    });

    it("should have valid block explorer", () => {
      const explorer = movementTestnet.blockExplorers?.default;
      expect(explorer).toBeDefined();
      expect(explorer?.name).toBe("Movement Explorer");
      expect(explorer?.url).toContain("explorer.movementnetwork.xyz");
    });

    it("should be marked as testnet", () => {
      expect(movementTestnet.testnet).toBe(true);
    });
  });

  describe("RPC URL Configuration", () => {
    it("should use default RPC URL if environment variable not provided", () => {
      const rpcUrl = movementMainnet.rpcUrls.default.http[0];
      expect(rpcUrl).toBe("https://full.mainnet.movementinfra.xyz/v1");
    });

    it("should use default testnet RPC URL if environment variable not provided", () => {
      const rpcUrl = movementTestnet.rpcUrls.default.http[0];
      expect(rpcUrl).toBe("https://testnet.movementnetwork.xyz/v1");
    });
  });
});
