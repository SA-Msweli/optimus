module optimus::did {
    use std::signer;
    use std::vector;
    use aptos_framework::timestamp;

    const ERR_DID_ALREADY_EXISTS: u64 = 1;
    const ERR_DID_NOT_EXISTS: u64 = 2;

    struct DID has key {
        owner: address,
        created_at: u64,
        last_activity: u64,
        risk_profile_score: u64,
        risk_profile_key: vector<u8>,
        transaction_count: u64,
        total_volume: u64,
        successful_loans: u64,
        defaulted_loans: u64,
        governance_participation: u64,
    }

    struct DIDRegistry has key {
        total_dids: u64,
    }

    fun init_module(sender: &signer) {
        move_to(sender, DIDRegistry {
            total_dids: 0,
        });
    }

    public entry fun create_did(sender: &signer) acquires DIDRegistry {
        let sender_addr = signer::address_of(sender);

        assert!(!exists<DID>(sender_addr), ERR_DID_ALREADY_EXISTS);

        let registry = borrow_global_mut<DIDRegistry>(@optimus);
        let current_time = timestamp::now_seconds();

        let new_did = DID {
            owner: sender_addr,
            created_at: current_time,
            last_activity: current_time,
            risk_profile_score: 0,
            risk_profile_key: vector::empty(),
            transaction_count: 0,
            total_volume: 0,
            successful_loans: 0,
            defaulted_loans: 0,
            governance_participation: 0,
        };

        registry.total_dids += 1;

        move_to(sender, new_did);
    }

    public entry fun update_risk_profile(
        owner_addr: address,
        new_score: u64,
        risk_profile_key: vector<u8>
    ) acquires DID {
        assert!(exists<DID>(owner_addr), ERR_DID_NOT_EXISTS);

        let did = borrow_global_mut<DID>(owner_addr);

        if (new_score <= 100) {
            did.risk_profile_score = new_score;
        };

        did.risk_profile_key = risk_profile_key;
        did.last_activity = timestamp::now_seconds();
    }

    public entry fun update_transaction_history(
        owner_addr: address,
        transaction_count: u64,
        total_volume: u64
    ) acquires DID {
        assert!(exists<DID>(owner_addr), ERR_DID_NOT_EXISTS);

        let did = borrow_global_mut<DID>(owner_addr);
        did.transaction_count = transaction_count;
        did.total_volume = total_volume;
        did.last_activity = timestamp::now_seconds();
    }

    public entry fun update_lending_history(
        owner_addr: address,
        successful_loans: u64,
        defaulted_loans: u64
    ) acquires DID {
        assert!(exists<DID>(owner_addr), ERR_DID_NOT_EXISTS);

        let did = borrow_global_mut<DID>(owner_addr);
        did.successful_loans = successful_loans;
        did.defaulted_loans = defaulted_loans;
        did.last_activity = timestamp::now_seconds();
    }

    public entry fun update_governance_participation(
        owner_addr: address,
        participation_count: u64
    ) acquires DID {
        assert!(exists<DID>(owner_addr), ERR_DID_NOT_EXISTS);

        let did = borrow_global_mut<DID>(owner_addr);
        did.governance_participation = participation_count;
        did.last_activity = timestamp::now_seconds();
    }

    #[view]
    public fun did_exists(owner_addr: address): bool {
        exists<DID>(owner_addr)
    }

    #[view]
    public fun get_did_info(owner_addr: address): (
        address,
        u64,
        u64,
        u64,
        u64,
        u64,
        u64,
        u64,
        u64,
    ) acquires DID {
        assert!(exists<DID>(owner_addr), ERR_DID_NOT_EXISTS);

        let did = borrow_global<DID>(owner_addr);
        (
            did.owner,
            did.created_at,
            did.last_activity,
            did.risk_profile_score,
            did.transaction_count,
            did.total_volume,
            did.successful_loans,
            did.defaulted_loans,
            did.governance_participation,
        )
    }

    #[view]
    public fun get_risk_profile_score(owner_addr: address): u64 acquires DID {
        if (!exists<DID>(owner_addr)) {
            return 0
        };

        let did = borrow_global<DID>(owner_addr);
        did.risk_profile_score
    }

    #[view]
    public fun get_risk_profile_key(owner_addr: address): vector<u8> acquires DID {
        if (!exists<DID>(owner_addr)) {
            return vector::empty()
        };

        let did = borrow_global<DID>(owner_addr);
        did.risk_profile_key
    }

    #[view]
    public fun get_lending_history(owner_addr: address): (u64, u64) acquires DID {
        if (!exists<DID>(owner_addr)) {
            return (0, 0)
        };

        let did = borrow_global<DID>(owner_addr);
        (did.successful_loans, did.defaulted_loans)
    }

    #[view]
    public fun get_total_dids(): u64 acquires DIDRegistry {
        let registry = borrow_global<DIDRegistry>(@optimus);
        registry.total_dids
    }

    #[test_only]
    public fun init_module_for_test(sender: &signer) {
        init_module(sender);
    }
}
