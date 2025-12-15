/**
 * P2P Payment Service
 * 
 * This service provides functionality for peer-to-peer payments with
 * address validation.
 */

import { transferToken } from '../entry-functions/transfer';
import { InputTransactionData } from '@aptos-labs/wallet-adapter-react';

export interface PaymentValidationResult {
  isValid: boolean;
  warnings: string[];
  riskLevel: 'low' | 'medium' | 'high';
}

export interface PaymentRequest {
  recipient: string;
  amount: number;
  coinType: string;
  memo?: string;
}

/**
 * PaymentService class for P2P payments
 */
export class PaymentService {

  /**
   * Validate recipient address
   * @param address - Recipient address to validate
   * @returns Promise<PaymentValidationResult> - Validation result with warnings
   */
  async validateRecipientAddress(address: string): Promise<PaymentValidationResult> {
    const warnings: string[] = [];
    let riskLevel: 'low' | 'medium' | 'high' = 'low';

    try {
      // Basic address format validation
      if (!this.isValidAptosAddress(address)) {
        return {
          isValid: false,
          warnings: ['Invalid Aptos address format'],
          riskLevel: 'high'
        };
      }

      return {
        isValid: true,
        warnings,
        riskLevel
      };

    } catch (error) {
      console.error('Address validation failed:', error);
      return {
        isValid: false,
        warnings: ['Address validation failed - please check the address and try again'],
        riskLevel: 'high'
      };
    }
  }

  /**
   * Prepare payment transaction
   * @param paymentRequest - Payment details
   * @returns InputTransactionData - Transaction data for wallet submission
   */
  preparePaymentTransaction(paymentRequest: PaymentRequest): InputTransactionData {
    const { recipient, amount, coinType } = paymentRequest;

    return transferToken({
      recipient,
      amount,
      coinType
    });
  }

  /**
   * Validate payment amount
   * @param amount - Amount to validate
   * @param balance - Current balance
   * @param coinType - Coin type
   * @returns Object with validation result
   */
  validatePaymentAmount(amount: number, balance: number, coinType: string = "0x1::aptos_coin::AptosCoin"): {
    isValid: boolean;
    error?: string;
  } {
    if (amount <= 0) {
      return {
        isValid: false,
        error: 'Amount must be greater than 0'
      };
    }

    if (amount > balance) {
      return {
        isValid: false,
        error: 'Insufficient balance'
      };
    }

    // Check minimum transfer amount (1 unit in smallest denomination)
    if (amount < 1) {
      const tokenInfo = this.getTokenInfo(coinType);
      const symbol = tokenInfo?.symbol || 'tokens';
      return {
        isValid: false,
        error: `Minimum transfer amount is 1 unit of ${symbol}`
      };
    }

    return { isValid: true };
  }

  /**
   * Format amount for display
   * @param amount - Amount in smallest units
   * @param decimals - Number of decimals
   * @returns Formatted amount string
   */
  formatAmount(amount: number, decimals: number = 8): string {
    return (amount / Math.pow(10, decimals)).toFixed(decimals);
  }

  /**
   * Parse amount from user input to smallest units
   * @param amountStr - Amount string from user input
   * @param decimals - Number of decimals
   * @returns Amount in smallest units
   */
  parseAmount(amountStr: string, decimals: number = 8): number {
    const amount = parseFloat(amountStr);
    if (isNaN(amount)) {
      throw new Error('Invalid amount format');
    }
    return Math.floor(amount * Math.pow(10, decimals));
  }

  /**
   * Basic Aptos address format validation
   * @param address - Address to validate
   * @returns boolean - Whether address format is valid
   */
  private isValidAptosAddress(address: string): boolean {
    // Aptos addresses are 32-byte hex strings, can be with or without 0x prefix
    // Can be shortened (without leading zeros)
    const hexPattern = /^(0x)?[a-fA-F0-9]{1,64}$/;

    if (!hexPattern.test(address)) {
      return false;
    }

    // Remove 0x prefix if present
    const cleanAddress = address.startsWith('0x') ? address.slice(2) : address;

    // Should not be longer than 64 characters (32 bytes)
    return cleanAddress.length <= 64;
  }

  /**
   * Normalize address format
   * @param address - Address to normalize
   * @returns Normalized address with 0x prefix
   */
  normalizeAddress(address: string): string {
    if (!this.isValidAptosAddress(address)) {
      throw new Error('Invalid address format');
    }

    // Add 0x prefix if not present
    if (!address.startsWith('0x')) {
      return '0x' + address;
    }

    return address;
  }

  /**
   * Get supported coin types
   * @returns Array of supported coin types
   */
  getSupportedCoinTypes(): Array<{ coinType: string; name: string; symbol: string; decimals: number }> {
    return [
      {
        coinType: "0x1::aptos_coin::AptosCoin",
        name: "Aptos Coin",
        symbol: "APT",
        decimals: 8
      },
      {
        coinType: "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC",
        name: "USD Coin",
        symbol: "USDC",
        decimals: 6
      },
      {
        coinType: "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDT",
        name: "Tether USD",
        symbol: "USDT",
        decimals: 6
      },
      {
        coinType: "0x1::aptos_coin::AptosCoin", // Placeholder for WETH
        name: "Wrapped Ethereum",
        symbol: "WETH",
        decimals: 8
      }
      // Additional coin types can be added here
    ];
  }

  /**
   * Get token info by coin type
   * @param coinType - The coin type to get info for
   * @returns Token info or null if not found
   */
  getTokenInfo(coinType: string): { coinType: string; name: string; symbol: string; decimals: number } | null {
    const supportedTokens = this.getSupportedCoinTypes();
    return supportedTokens.find(token => token.coinType === coinType) || null;
  }

  /**
   * Get user's balance for a specific token
   * @param address - User's address
   * @param coinType - Token type to get balance for
   * @returns Promise<number> - Balance in smallest units
   */
  async getTokenBalance(address: string, coinType: string): Promise<number> {
    try {
      // Use Aptos SDK for balance queries
      if (coinType === "0x1::aptos_coin::AptosCoin") {
        const { aptosClient } = await import('@/utils/aptosClient');
        const aptos = aptosClient();
        const balance = await aptos.getAccountAPTAmount({ accountAddress: address });
        return balance;
      }

      return 0;
    } catch (error) {
      console.error('Failed to get token balance:', error);
      return 0;
    }
  }

  /**
   * Get all token balances for a user
   * @param address - User's address
   * @returns Promise<Array> - Array of token balances
   */
  async getAllTokenBalances(address: string): Promise<Array<{
    coinType: string;
    name: string;
    symbol: string;
    decimals: number;
    balance: number;
    formattedBalance: string;
  }>> {
    const supportedTokens = this.getSupportedCoinTypes();
    const balances = [];

    for (const token of supportedTokens) {
      try {
        const balance = await this.getTokenBalance(address, token.coinType);
        balances.push({
          ...token,
          balance,
          formattedBalance: this.formatAmount(balance, token.decimals)
        });
      } catch (error) {
        console.error(`Failed to get balance for ${token.symbol}:`, error);
        balances.push({
          ...token,
          balance: 0,
          formattedBalance: '0.00'
        });
      }
    }

    return balances;
  }
}

// Export singleton instance
export const paymentService = new PaymentService();

export default paymentService;