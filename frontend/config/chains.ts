import { defineChain } from "viem";

/**
 * Movement Mainnet Configuration
 * Chain ID: 126
 */
export const movementMainnet = defineChain({
  id: 126,
  name: "Movement Mainnet",
  network: "movement-mainnet",
  nativeCurrency: {
    decimals: 8,
    name: "MOVE",
    symbol: "MOVE",
  },
  rpcUrls: {
    default: {
      http: [import.meta.env.VITE_MOVEMENT_RPC_URL || "https://full.mainnet.movementinfra.xyz/v1"],
    },
  },
  blockExplorers: {
    default: {
      name: "Movement Explorer",
      url: "https://explorer.movementnetwork.xyz/?network=mainnet",
    },
  },
});

/**
 * Movement Testnet Configuration
 * Chain ID: 250
 */
export const movementTestnet = defineChain({
  id: 250,
  name: "Movement Testnet",
  network: "movement-testnet",
  nativeCurrency: {
    decimals: 8,
    name: "MOVE",
    symbol: "MOVE",
  },
  rpcUrls: {
    default: {
      http: [import.meta.env.VITE_MOVEMENT_TESTNET_RPC_URL || "https://testnet.movementnetwork.xyz/v1"],
    },
  },
  blockExplorers: {
    default: {
      name: "Movement Explorer",
      url: "https://explorer.movementnetwork.xyz/?network=bardock+testnet",
    },
  },
  testnet: true,
});
