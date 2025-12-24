module optimus::bnpl {
    use std::signer;
    use aptos_framework::timestamp;

    const ERR_BNPL_NOT_EXISTS: u64 = 1;
    const ERR_INVALID_AMOUNT: u64 = 2;
    const ERR_INVALID_INSTALLMENT: u64 = 3;
    const ERR_PAYMENT_ALREADY_MADE: u64 = 4;

    struct BNPLArrangement has key {
        id: u64,
        payer: address,
        recipient: address,
        total_amount: u64,
        installment_amount: u64,
        late_fee_bps: u64,
        created_at: u64,
    }

    struct BNPLRegistry has key {
        total_arrangements: u64,
    }

    fun init_module(sender: &signer) {
        move_to(sender, BNPLRegistry {
            total_arrangements: 0,
        });
    }

    public entry fun create_bnpl(
        payer: &signer,
        recipient: address,
        total_amount: u64,
        late_fee_bps: u64,
    ) acquires BNPLRegistry {
        let payer_addr = signer::address_of(payer);
        assert!(total_amount > 0, ERR_INVALID_AMOUNT);

        let registry = borrow_global_mut<BNPLRegistry>(@optimus);
        let arrangement_id = registry.total_arrangements;
        registry.total_arrangements += 1;

        let installment_amount = total_amount / 3;

        let arrangement = BNPLArrangement {
            id: arrangement_id,
            payer: payer_addr,
            recipient,
            total_amount,
            installment_amount,
            late_fee_bps,
            created_at: timestamp::now_seconds(),
        };

        move_to(payer, arrangement);
    }

    public entry fun make_payment(
        payer: &signer,
        arrangement_addr: address,
        installment_number: u64,
        payment_amount: u64,
    ) acquires BNPLArrangement {
        let payer_addr = signer::address_of(payer);
        assert!(installment_number >= 1 && installment_number <= 3, ERR_INVALID_INSTALLMENT);
        assert!(payment_amount > 0, ERR_INVALID_AMOUNT);
        assert!(exists<BNPLArrangement>(arrangement_addr), ERR_BNPL_NOT_EXISTS);

        let arrangement = borrow_global_mut<BNPLArrangement>(arrangement_addr);
        assert!(arrangement.payer == payer_addr, ERR_BNPL_NOT_EXISTS);

    }

    public entry fun apply_late_fee(
        _applier: &signer,
        arrangement_addr: address,
        installment_number: u64,
    ) acquires BNPLArrangement {
        assert!(installment_number >= 1 && installment_number <= 3, ERR_INVALID_INSTALLMENT);
        assert!(exists<BNPLArrangement>(arrangement_addr), ERR_BNPL_NOT_EXISTS);

        let arrangement = borrow_global_mut<BNPLArrangement>(arrangement_addr);

        let _late_fee = (arrangement.installment_amount * 500) / 10000;

        // Late fee distribution to DAO members happens via backend workflow
        // Backend calculates: late_fee = (installment_amount * 500) / 10000 (5% penalty)
        // Then distributes proportionally to DAO members based on voting power
    }

    #[view]
    public fun get_arrangement_info(arrangement_addr: address): (
        u64,
        address,
        address,
        u64,
        u64,
        u64,
    ) acquires BNPLArrangement {
        assert!(exists<BNPLArrangement>(arrangement_addr), ERR_BNPL_NOT_EXISTS);

        let arrangement = borrow_global<BNPLArrangement>(arrangement_addr);
        (
            arrangement.id,
            arrangement.payer,
            arrangement.recipient,
            arrangement.total_amount,
            arrangement.installment_amount,
            arrangement.late_fee_bps,
        )
    }

    #[view]
    public fun get_total_arrangements(): u64 acquires BNPLRegistry {
        let registry = borrow_global<BNPLRegistry>(@optimus);
        registry.total_arrangements
    }

    #[test_only]
    public fun init_module_for_test(sender: &signer) {
        init_module(sender);
    }
}
