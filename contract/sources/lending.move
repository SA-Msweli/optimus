module optimus::lending {
    use std::signer;
    use aptos_framework::timestamp;

    const ERR_LOAN_NOT_EXISTS: u64 = 1;
    const ERR_INSUFFICIENT_DAO_FUNDS: u64 = 2;
    const ERR_INVALID_AMOUNT: u64 = 3;
    const ERR_LOAN_NOT_ACTIVE: u64 = 4;
    const ERR_PAYMENT_EXCEEDS_OWED: u64 = 5;

    struct Loan has key {
        id: u64,
        borrower: address,
        dao_addr: address,
        principal: u64,
        interest_rate_bps: u64,
        start_time: u64,
        end_time: u64,
        amount_paid: u64,
        status: u8,
    }

    struct LendingRegistry has key {
        total_loans: u64,
    }

    fun init_module(sender: &signer) {
        move_to(sender, LendingRegistry {
            total_loans: 0,
        });
    }

    public entry fun create_loan(
        borrower: &signer,
        dao_addr: address,
        principal: u64,
        interest_rate_bps: u64,
        duration_seconds: u64,
    ) acquires LendingRegistry {
        let borrower_addr = signer::address_of(borrower);
        assert!(principal > 0, ERR_INVALID_AMOUNT);

        let registry = borrow_global_mut<LendingRegistry>(@optimus);
        let loan_id = registry.total_loans;
        registry.total_loans += 1;

        let current_time = timestamp::now_seconds();

        let loan = Loan {
            id: loan_id,
            borrower: borrower_addr,
            dao_addr,
            principal,
            interest_rate_bps,
            start_time: current_time,
            end_time: current_time + duration_seconds,
            amount_paid: 0,
            status: 0,
        };

        move_to(borrower, loan);
    }

    public entry fun approve_loan(
        _approver: &signer,
        loan_addr: address,
    ) acquires Loan {
        assert!(exists<Loan>(loan_addr), ERR_LOAN_NOT_EXISTS);

        let loan = borrow_global_mut<Loan>(loan_addr);
        assert!(loan.status == 0, ERR_LOAN_NOT_ACTIVE);

        loan.status = 1;
    }

    public entry fun make_payment(
        borrower: &signer,
        loan_addr: address,
        payment_amount: u64,
    ) acquires Loan {
        let borrower_addr = signer::address_of(borrower);
        assert!(payment_amount > 0, ERR_INVALID_AMOUNT);
        assert!(exists<Loan>(loan_addr), ERR_LOAN_NOT_EXISTS);

        let loan = borrow_global_mut<Loan>(loan_addr);
        assert!(loan.borrower == borrower_addr, ERR_LOAN_NOT_ACTIVE);
        assert!(loan.status == 1, ERR_LOAN_NOT_ACTIVE);

        let current_time = timestamp::now_seconds();
        let time_elapsed = if (current_time > loan.end_time) {
            loan.end_time - loan.start_time
        } else {
            current_time - loan.start_time
        };

        let interest = (loan.principal * loan.interest_rate_bps * time_elapsed) / (10000 * 365 * 24 * 60 * 60);
        let total_owed = loan.principal + interest;
        let amount_remaining = total_owed - loan.amount_paid;

        assert!(payment_amount <= amount_remaining, ERR_PAYMENT_EXCEEDS_OWED);

        loan.amount_paid += payment_amount;

        if (loan.amount_paid >= total_owed) {
            loan.status = 2;
        };

        // Interest distribution to DAO members happens via backend workflow
        // Backend calculates: interest = (principal * interest_rate_bps * time_elapsed) / (10000 * 365 * 24 * 60 * 60)
        // Then distributes proportionally to DAO members based on voting power
    }

    public entry fun mark_defaulted(
        _marker: &signer,
        loan_addr: address,
    ) acquires Loan {
        assert!(exists<Loan>(loan_addr), ERR_LOAN_NOT_EXISTS);

        let loan = borrow_global_mut<Loan>(loan_addr);

        let current_time = timestamp::now_seconds();
        assert!(current_time > loan.end_time, ERR_LOAN_NOT_ACTIVE);

        loan.status = 3;
    }

    #[view]
    public fun get_loan_info(loan_addr: address): (
        u64,
        address,
        address,
        u64,
        u64,
        u64,
        u64,
        u8,
    ) acquires Loan {
        assert!(exists<Loan>(loan_addr), ERR_LOAN_NOT_EXISTS);

        let loan = borrow_global<Loan>(loan_addr);
        (
            loan.id,
            loan.borrower,
            loan.dao_addr,
            loan.principal,
            loan.interest_rate_bps,
            loan.start_time,
            loan.end_time,
            loan.status,
        )
    }

    #[view]
    public fun get_total_loans(): u64 acquires LendingRegistry {
        let registry = borrow_global<LendingRegistry>(@optimus);
        registry.total_loans
    }

    #[test_only]
    public fun init_module_for_test(sender: &signer) {
        init_module(sender);
    }
}
