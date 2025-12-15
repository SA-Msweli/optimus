import { PropsWithChildren } from "react";
import { PrivyProvider } from "@privy-io/react-auth";
import { movementMainnet, movementTestnet } from "@/config/chains";

export function PrivyProviderWrapper({ children }: PropsWithChildren) {
  const appId = import.meta.env.VITE_PRIVY_APP_ID;
  const clientId = import.meta.env.VITE_PRIVY_CLIENT_ID;

  if (!appId || !clientId) {
    throw new Error(
      "Missing Privy configuration. Please set VITE_PRIVY_APP_ID and VITE_PRIVY_CLIENT_ID in your environment variables."
    );
  }

  return (
    <PrivyProvider
      appId={appId}
      clientId={clientId}
      config={{
        embeddedWallets: {
          createOnLogin: "users-without-wallets",
        },
        defaultChain: movementMainnet,
        supportedChains: [movementMainnet, movementTestnet],
        appearance: {
          theme: "light",
          accentColor: "#676FFF",
          logo: "https://optimus.example.com/logo.png",
        },
      }}
    >
      {children}
    </PrivyProvider>
  );
}
