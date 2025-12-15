/**
 * Simple Credit Service
 * 
 * Simplified version for testing credit score functionality
 */

/**
 * Simplified credit score metrics
 */
export interface SimpleCreditMetrics {
  address: string;
  credit_score: number; // 300-850 range
  credit_grade: 'A+' | 'A' | 'B+' | 'B' | 'C+' | 'C' | 'D' | 'F';
  risk_tier: 'Prime' | 'Near Prime' | 'Subprime' | 'Deep Subprime';

  // Payment factors
  payment_score: number; // 0-100
  utilization_score: number; // 0-100
  history_score: number; // 0-100

  // Risk assessment
  probability_of_default: number; // 0-100%
  max_recommended_loan: string;
  recommended_interest_rate: number; // APR %
  collateral_requirement: number; // % of loan value

  // Traditional metrics for compatibility
  transaction_count: number;
  total_volume: string;
  unique_counterparties: number;
  governance_participation: number;
  // reputation_score removed
  risk_level: 'low' | 'medium' | 'high';
  last_updated: number;
}

/**
 * Simple Credit Service class
 */
export class SimpleCreditService {
  /**
   * Calculate credit score for an address
   * Note: This is a simplified implementation that returns default scores
   * since external data sources have been removed
   */
  async calculateCreditScore(address: string): Promise<SimpleCreditMetrics> {
    try {
      // Return default credit score for now
      // In the future, this could be integrated with on-chain DID data
      return this.getDefaultCreditScore(address);
    } catch (error) {
      console.error(`Failed to calculate credit score for ${address}:`, error);
      return this.getDefaultCreditScore(address);
    }
  }



  /**
   * Calculate final credit score (300-850 range)
   */
  private calculateFinalCreditScore(paymentScore: number, utilizationScore: number, historyScore: number): number {
    // Weighted average (FICO-style weights)
    const weightedScore = (
      paymentScore * 0.35 +      // Payment history: 35%
      utilizationScore * 0.30 +  // Credit utilization: 30%
      historyScore * 0.15 +      // Credit history: 15%
      75 * 0.20                  // Credit mix + new credit: 20% (default to 75)
    );

    // Map 0-100 to 300-850 range
    const creditScore = 300 + (weightedScore / 100) * 550;

    return Math.round(Math.max(300, Math.min(850, creditScore)));
  }

  /**
   * Get credit grade based on score
   */
  private getCreditGrade(score: number): SimpleCreditMetrics['credit_grade'] {
    if (score >= 800) return 'A+';
    if (score >= 740) return 'A';
    if (score >= 670) return 'B+';
    if (score >= 580) return 'B';
    if (score >= 500) return 'C+';
    if (score >= 400) return 'C';
    if (score >= 350) return 'D';
    return 'F';
  }

  /**
   * Get risk tier based on score
   */
  private getRiskTier(score: number): SimpleCreditMetrics['risk_tier'] {
    if (score >= 660) return 'Prime';
    if (score >= 580) return 'Near Prime';
    if (score >= 500) return 'Subprime';
    return 'Deep Subprime';
  }

  /**
   * Calculate risk assessment
   */
  private calculateRiskAssessment(creditScore: number, paymentScore: number) {
    // Probability of default
    let probabilityOfDefault = 0;
    if (creditScore >= 750) probabilityOfDefault = 2;
    else if (creditScore >= 700) probabilityOfDefault = 5;
    else if (creditScore >= 650) probabilityOfDefault = 10;
    else if (creditScore >= 600) probabilityOfDefault = 20;
    else if (creditScore >= 550) probabilityOfDefault = 35;
    else probabilityOfDefault = 50;

    // Adjust based on payment score
    if (paymentScore < 50) probabilityOfDefault += 15;

    // Max recommended loan
    const baseAmount = Math.max(0, (creditScore - 300) * 100);
    const maxLoan = Math.round(baseAmount);

    // Interest rate
    let interestRate = 25; // Base rate
    if (creditScore >= 750) interestRate = 5;
    else if (creditScore >= 700) interestRate = 8;
    else if (creditScore >= 650) interestRate = 12;
    else if (creditScore >= 600) interestRate = 16;
    else if (creditScore >= 550) interestRate = 20;

    // Collateral requirement
    let collateralRequirement = 200; // 200% for lowest scores
    if (creditScore >= 750) collateralRequirement = 110;
    else if (creditScore >= 700) collateralRequirement = 125;
    else if (creditScore >= 650) collateralRequirement = 140;
    else if (creditScore >= 600) collateralRequirement = 160;
    else if (creditScore >= 550) collateralRequirement = 180;

    return {
      probability_of_default: Math.min(100, probabilityOfDefault),
      max_recommended_loan: maxLoan.toString(),
      recommended_interest_rate: interestRate,
      collateral_requirement: collateralRequirement,
    };
  }



  /**
   * Map credit score to traditional risk level
   */
  private mapToRiskLevel(creditScore: number): 'low' | 'medium' | 'high' {
    if (creditScore >= 670) return 'low';
    if (creditScore >= 580) return 'medium';
    return 'high';
  }

  /**
   * Get default credit score for new addresses
   */
  private getDefaultCreditScore(address: string): SimpleCreditMetrics {
    return {
      address,
      credit_score: 580, // Fair credit score
      credit_grade: 'B',
      risk_tier: 'Near Prime',

      payment_score: 50,
      utilization_score: 100,
      history_score: 0,

      probability_of_default: 20,
      max_recommended_loan: '5000',
      recommended_interest_rate: 16,
      collateral_requirement: 160,

      transaction_count: 0,
      total_volume: '0',
      unique_counterparties: 0,
      governance_participation: 0,
      // reputation_score removed
      risk_level: 'medium',
      last_updated: Date.now(),
    };
  }
}

// Export singleton instance
export const simpleCreditService = new SimpleCreditService();

export default simpleCreditService;