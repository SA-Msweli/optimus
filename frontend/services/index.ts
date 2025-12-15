/**
 * Services Index
 * 
 * Central export point for all service modules
 */

export { PaymentService, paymentService } from './paymentService';
export { VaultService, vaultService } from './vaultService';
export { LendingService, lendingService } from './lendingService';
export type {
  VaultInfo,
  VaultPosition,
  VaultPerformance,
  CreateVaultParams,
  DepositParams,
  WithdrawParams,
  VaultStats,
} from './vaultService';
export type {
  LoanDetails,
  PaymentSchedule,
  NextPayment,
  LoanRequest,
} from './lendingService';