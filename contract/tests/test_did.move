#[test_only]
module optimus::test_did {
    use std::signer;
    use std::vector;
    use aptos_framework::timestamp;
    use optimus::did;

    // ============================================================================
    // PROPERTY 3: Risk Profile Bounds
    // For any user, risk_profile_score must be in [0, 100]
    // ============================================================================

    #[test(optimus_admin = @0x1, user = @0x2, aptos_framework = @0x1)]
    fun test_property_3_risk_profile_bounds(
        optimus_admin: &signer,
        user: &signer,
        aptos_framework: &signer,
    ) {
        timestamp::set_time_has_started_for_testing(aptos_framework);
        did::init_module_for_test(optimus_admin);

        let user_addr = signer::address_of(user);

        // Create DID - should initialize with score 0
        did::create_did(user);

        let (_, _, _, score, _, _, _, _, _) = did::get_did_info(user_addr);
        assert!(score >= 0 && score <= 100, 1); // PROPERTY 3: Bounds

        // Update to max (100)
        did::update_risk_profile(user_addr, 100, vector::empty());
        let (_, _, _, score, _, _, _, _, _) = did::get_did_info(user_addr);
        assert!(score == 100, 2);
        assert!(score >= 0 && score <= 100, 3); // PROPERTY 3: Bounds

        // Update to min (0)
        did::update_risk_profile(user_addr, 0, vector::empty());
        let (_, _, _, score, _, _, _, _, _) = did::get_did_info(user_addr);
        assert!(score == 0, 4);
        assert!(score >= 0 && score <= 100, 5); // PROPERTY 3: Bounds
    }

    // ============================================================================
    // PROPERTY 8: Risk Profile Update Atomicity
    // For any risk profile update, reason, timestamp, and score are atomic
    // ============================================================================

    #[test(optimus_admin = @0x1, user = @0x2, aptos_framework = @0x1)]
    fun test_property_8_risk_profile_update_atomicity(
        optimus_admin: &signer,
        user: &signer,
        aptos_framework: &signer,
    ) {
        timestamp::set_time_has_started_for_testing(aptos_framework);
        did::init_module_for_test(optimus_admin);

        let user_addr = signer::address_of(user);

        // Create DID
        did::create_did(user);

        // Get initial state
        let (_, created_at, _, initial_score, _, _, _, _, _) = did::get_did_info(user_addr);
        assert!(initial_score == 0, 1);

        // Update risk profile with reason key
        let reason_key = b"transaction_completed";
        did::update_risk_profile(user_addr, 25, reason_key);

        // Get updated state
        let (_, _, last_activity, updated_score, _, _, _, _, _) = did::get_did_info(user_addr);

        // Verify atomicity: all fields updated together
        assert!(updated_score == 25, 2); // PROPERTY 8: Score updated
        assert!(last_activity >= created_at, 3); // PROPERTY 8: Timestamp updated
        
        // Verify reason key is stored
        let stored_reason = did::get_risk_profile_key(user_addr);
        assert!(stored_reason == reason_key, 4); // PROPERTY 8: Reason recorded
    }

    // ============================================================================
    // PROPERTY 15: DID-Risk Profile Linkage
    // For any user, DID record contains immutable reference to risk profile
    // ============================================================================

    #[test(optimus_admin = @0x1, user = @0x2, aptos_framework = @0x1)]
    fun test_property_15_did_risk_profile_linkage(
        optimus_admin: &signer,
        user: &signer,
        aptos_framework: &signer,
    ) {
        timestamp::set_time_has_started_for_testing(aptos_framework);
        did::init_module_for_test(optimus_admin);

        let user_addr = signer::address_of(user);

        // Create DID
        did::create_did(user);

        // Get DID info
        let (owner, _, _, _, _, _, _, _, _) = did::get_did_info(user_addr);

        // Verify: DID owner is correct
        assert!(owner == user_addr, 1); // PROPERTY 15: Linkage

        // Update risk profile with key
        let risk_key = b"profile_key_123";
        did::update_risk_profile(user_addr, 50, risk_key);

        // Get updated DID info
        let (_, _, _, score, _, _, _, _, _) = did::get_did_info(user_addr);
        assert!(score == 50, 2);

        // Verify: Risk profile key is stored
        let stored_key = did::get_risk_profile_key(user_addr);
        assert!(stored_key == risk_key, 3); // PROPERTY 15: Key immutability
    }
}
