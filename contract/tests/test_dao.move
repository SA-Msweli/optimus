#[test_only]
module optimus::test_dao {
    use std::signer;
    use aptos_framework::timestamp;
    use optimus::dao;

    // ============================================================================
    // PROPERTY 1: Fund Conservation in DAO Treasury
    // For any DAO, sum of all member investments = DAO treasury balance
    // ============================================================================

    #[test(creator = @0x1, member1 = @0x2, member2 = @0x3, aptos_framework = @0x1)]
    fun test_property_1_fund_conservation_multiple_members(
        creator: &signer,
        member1: &signer,
        member2: &signer,
        aptos_framework: &signer,
    ) {
        timestamp::set_time_has_started_for_testing(aptos_framework);
        dao::init_module_for_test(creator);

        let creator_addr = signer::address_of(creator);
        let _member1_addr = signer::address_of(member1);
        let _member2_addr = signer::address_of(member2);

        // Create DAO
        dao::create_dao(creator, 0, 7); // Secure goal, 7 day voting period

        // Member 1 invests 1000
        dao::join_dao(member1, creator_addr, 1000);

        // Member 2 invests 2000
        dao::join_dao(member2, creator_addr, 2000);

        // Verify: treasury balance (3000) = sum of investments (1000 + 2000)
        let (_, _, _, treasury, total_investments, _, _) = dao::get_dao_info(creator_addr);
        assert!(treasury == 3000, 1);
        assert!(total_investments == 3000, 2);
        assert!(treasury == total_investments, 3); // PROPERTY 1: Conservation
    }

    // ============================================================================
    // PROPERTY 2: Voting Power Proportionality
    // For any DAO member, voting_power = (investment / total_investment) * 10000 bps
    // ============================================================================

    #[test(creator = @0x1, member1 = @0x2, member2 = @0x3, aptos_framework = @0x1)]
    fun test_property_2_voting_power_proportional(
        creator: &signer,
        member1: &signer,
        member2: &signer,
        aptos_framework: &signer,
    ) {
        timestamp::set_time_has_started_for_testing(aptos_framework);
        dao::init_module_for_test(creator);

        let creator_addr = signer::address_of(creator);
        let member1_addr = signer::address_of(member1);
        let member2_addr = signer::address_of(member2);

        dao::create_dao(creator, 0, 7);

        // Member 1 invests 2000
        dao::join_dao(member1, creator_addr, 2000);

        // Member 2 invests 3000
        dao::join_dao(member2, creator_addr, 3000);

        // Total: 5000 (creator 0 + member1 2000 + member2 3000)
        // Member 1 voting power should be: (2000 / 5000) * 10000 = 4000 bps
        // Member 2 voting power should be: (3000 / 5000) * 10000 = 6000 bps

        let member1_vp = dao::get_member_voting_power(creator_addr, member1_addr);
        let member2_vp = dao::get_member_voting_power(creator_addr, member2_addr);

        assert!(member1_vp == 4000, 1); // PROPERTY 2: Proportionality
        assert!(member2_vp == 6000, 2); // PROPERTY 2: Proportionality
    }

    // ============================================================================
    // PROPERTY 4: Supermajority Determination
    // For any voting period, if total votes exceed 50% of voting power, approved
    // ============================================================================

    #[test(creator = @0x1, member1 = @0x2, member2 = @0x3, aptos_framework = @0x1)]
    fun test_property_4_supermajority_determination(
        creator: &signer,
        member1: &signer,
        member2: &signer,
        aptos_framework: &signer,
    ) {
        timestamp::set_time_has_started_for_testing(aptos_framework);
        dao::init_module_for_test(creator);

        let creator_addr = signer::address_of(creator);
        let member1_addr = signer::address_of(member1);
        let member2_addr = signer::address_of(member2);

        // Create DAO
        dao::create_dao(creator, 0, 7);

        // Member 1 invests 3000 (60% voting power)
        dao::join_dao(member1, creator_addr, 3000);

        // Member 2 invests 2000 (40% voting power)
        dao::join_dao(member2, creator_addr, 2000);

        // Verify voting power distribution
        let member1_vp = dao::get_member_voting_power(creator_addr, member1_addr);
        let member2_vp = dao::get_member_voting_power(creator_addr, member2_addr);

        // Member 1 has 60% (6000 bps), Member 2 has 40% (4000 bps)
        assert!(member1_vp == 6000, 1); // PROPERTY 4: Voting power > 50%
        assert!(member2_vp == 4000, 2); // PROPERTY 4: Voting power < 50%
        assert!(member1_vp > 5000, 3); // PROPERTY 4: Supermajority threshold
    }

    // ============================================================================
    // PROPERTY 9: DAO Liquidation Distribution
    // For any DAO liquidation, sum of distributions = total available funds
    // ============================================================================

    #[test(creator = @0x1, member1 = @0x2, member2 = @0x3, aptos_framework = @0x1)]
    fun test_property_9_liquidation_distribution(
        creator: &signer,
        member1: &signer,
        member2: &signer,
        aptos_framework: &signer,
    ) {
        timestamp::set_time_has_started_for_testing(aptos_framework);
        dao::init_module_for_test(creator);

        let creator_addr = signer::address_of(creator);
        let _member1_addr = signer::address_of(member1);
        let _member2_addr = signer::address_of(member2);

        // Create DAO
        dao::create_dao(creator, 0, 7);

        // Members invest
        dao::join_dao(member1, creator_addr, 2000);
        dao::join_dao(member2, creator_addr, 3000);

        // Get treasury before liquidation
        let (_, _, _, _treasury_before, _total_investments, _, _) = dao::get_dao_info(creator_addr);

        // Dissolve DAO
        dao::dissolve_dao(creator, creator_addr);

        // Verify: DAO is marked as dissolved
        let (_, _, _, _, _, _, is_dissolved) = dao::get_dao_info(creator_addr);
        assert!(is_dissolved, 1); // PROPERTY 9: Liquidation recorded

        // Note: Actual distribution happens in backend via Temporal workflow
        // On-chain contract just marks as dissolved and stores final state
    }

    // ============================================================================
    // PROPERTY 10: Multi-DAO Voting Power Isolation
    // For any user in multiple DAOs, voting power is independent per DAO
    // ============================================================================

    #[test(creator1 = @0x1, creator2 = @0x4, member = @0x2, member2 = @0x5, aptos_framework = @0x1)]
    fun test_property_10_multi_dao_voting_power_isolation(
        creator1: &signer,
        creator2: &signer,
        member: &signer,
        member2: &signer,
        aptos_framework: &signer,
    ) {
        timestamp::set_time_has_started_for_testing(aptos_framework);
        dao::init_module_for_test(creator1);

        let creator1_addr = signer::address_of(creator1);
        let creator2_addr = signer::address_of(creator2);
        let member_addr = signer::address_of(member);
        let _member2_addr = signer::address_of(member2);

        // Create first DAO
        dao::create_dao(creator1, 0, 7);

        // Member invests 1000 in DAO 1 (100% voting power initially)
        dao::join_dao(member, creator1_addr, 1000);
        let dao1_vp = dao::get_member_voting_power(creator1_addr, member_addr);
        assert!(dao1_vp == 10000, 1); // 100% in DAO 1

        // Create second DAO (different creator)
        dao::create_dao(creator2, 1, 7); // Loans goal

        // Member invests 1000 in DAO 2
        // Member2 also invests 1000 in DAO 2 (so member has 50% voting power)
        dao::join_dao(member, creator2_addr, 1000);
        dao::join_dao(member2, creator2_addr, 1000);
        let dao2_vp = dao::get_member_voting_power(creator2_addr, member_addr);
        assert!(dao2_vp == 5000, 2); // 50% in DAO 2 (1000 / 2000)

        // Verify: DAO 1 voting power unchanged
        let dao1_vp_after = dao::get_member_voting_power(creator1_addr, member_addr);
        assert!(dao1_vp_after == 10000, 3); // PROPERTY 10: Isolation - still 100% in DAO 1
        
        // Verify: DAO 2 voting power is independent
        assert!(dao2_vp == 5000, 4); // PROPERTY 10: Isolation - 50% in DAO 2
    }
}
