module optimus::dao {
    use std::signer;
    use std::vector;
    use aptos_framework::timestamp;

    const ERR_DAO_NOT_EXISTS: u64 = 1;
    const ERR_NOT_DAO_MEMBER: u64 = 2;
    const ERR_INSUFFICIENT_FUNDS: u64 = 3;
    const ERR_INVALID_GOAL: u64 = 4;
    const ERR_DAO_ALREADY_EXISTS: u64 = 5;

    enum DAOGoal has store, drop, copy {
        Secure,
        Loans,
        BNPL,
    }

    struct DAO has key {
        creator: address,
        goal: DAOGoal,
        voting_period_seconds: u64,
        treasury_balance: u64,
        total_investments: u64,
        members: vector<Member>,
        created_at: u64,
        is_dissolved: bool,
    }

    struct Member has store, drop {
        address: address,
        investment_amount: u64,
        voting_power_bps: u64,
        joined_at: u64,
    }

    struct DAORegistry has key {
        total_daos: u64,
        dao_addresses: vector<address>,
    }

    fun init_module(sender: &signer) {
        move_to(sender, DAORegistry {
            total_daos: 0,
            dao_addresses: vector::empty(),
        });
    }

    public entry fun create_dao(
        creator: &signer,
        goal_type: u8,
        voting_period_days: u64,
    ) acquires DAORegistry {
        let creator_addr = signer::address_of(creator);

        assert!(goal_type <= 2, ERR_INVALID_GOAL);

        assert!(!exists<DAO>(creator_addr), ERR_DAO_ALREADY_EXISTS);

        let goal = goal_type_to_enum(goal_type);
        let current_time = timestamp::now_seconds();
        let voting_period_seconds = voting_period_days * 24 * 60 * 60;

        let members = vector::empty();
        vector::push_back(&mut members, Member {
            address: creator_addr,
            investment_amount: 0,
            voting_power_bps: 10000,
            joined_at: current_time,
        });

        let new_dao = DAO {
            creator: creator_addr,
            goal,
            voting_period_seconds,
            treasury_balance: 0,
            total_investments: 0,
            members,
            created_at: current_time,
            is_dissolved: false,
        };

        move_to(creator, new_dao);

        let registry = borrow_global_mut<DAORegistry>(@optimus);
        registry.total_daos += 1;
        vector::push_back(&mut registry.dao_addresses, creator_addr);
    }

    public entry fun join_dao(
        member: &signer,
        dao_addr: address,
        investment_amount: u64,
    ) acquires DAO {
        assert!(investment_amount > 0, ERR_INSUFFICIENT_FUNDS);
        assert!(exists<DAO>(dao_addr), ERR_DAO_NOT_EXISTS);

        let member_addr = signer::address_of(member);
        let dao = borrow_global_mut<DAO>(dao_addr);

        assert!(!dao.is_dissolved, ERR_DAO_NOT_EXISTS);

        let member_index = find_member_index(&dao.members, member_addr);

        if (member_index < vector::length(&dao.members)) {
            let member_ref = vector::borrow_mut(&mut dao.members, member_index);
            member_ref.investment_amount += investment_amount;
        } else {
            vector::push_back(&mut dao.members, Member {
                address: member_addr,
                investment_amount,
                voting_power_bps: 0,
                joined_at: timestamp::now_seconds(),
            });
        };

        dao.total_investments += investment_amount;
        dao.treasury_balance += investment_amount;

        recalculate_voting_power(&mut dao.members, dao.total_investments);
    }

    public entry fun dissolve_dao(
        creator: &signer,
        dao_addr: address,
    ) acquires DAO {
        let creator_addr = signer::address_of(creator);
        assert!(exists<DAO>(dao_addr), ERR_DAO_NOT_EXISTS);

        let dao = borrow_global_mut<DAO>(dao_addr);
        assert!(dao.creator == creator_addr, ERR_NOT_DAO_MEMBER);

        dao.is_dissolved = true;

        // Fund distribution on liquidation happens via backend workflow
        // Backend calculates: member_share = (member_investment / total_investments) * treasury_balance
        // Then distributes proportionally to each member using 0x1::coin::transfer
    }

    #[view]
    public fun dao_exists(dao_addr: address): bool {
        exists<DAO>(dao_addr)
    }

    #[view]
    public fun get_dao_info(dao_addr: address): (
        address,
        u8,
        u64,
        u64,
        u64,
        u64,
        bool,
    ) acquires DAO {
        assert!(exists<DAO>(dao_addr), ERR_DAO_NOT_EXISTS);
        
        let dao = borrow_global<DAO>(dao_addr);
        (
            dao.creator,
            goal_enum_to_type(&dao.goal),
            dao.voting_period_seconds,
            dao.treasury_balance,
            dao.total_investments,
            vector::length(&dao.members),
            dao.is_dissolved,
        )
    }

    #[view]
    public fun get_member_voting_power(dao_addr: address, member_addr: address): u64 acquires DAO {
        if (!exists<DAO>(dao_addr)) {
            return 0
        };

        let dao = borrow_global<DAO>(dao_addr);
        let member_index = find_member_index(&dao.members, member_addr);

        if (member_index < vector::length(&dao.members)) {
            let member = vector::borrow(&dao.members, member_index);
            member.voting_power_bps
        } else {
            0
        }
    }

    #[view]
    public fun get_total_daos(): u64 acquires DAORegistry {
        let registry = borrow_global<DAORegistry>(@optimus);
        registry.total_daos
    }


    fun goal_type_to_enum(goal_type: u8): DAOGoal {
        if (goal_type == 0) {
            DAOGoal::Secure
        } else if (goal_type == 1) {
            DAOGoal::Loans
        } else {
            DAOGoal::BNPL
        }
    }

    fun goal_enum_to_type(goal: &DAOGoal): u8 {
        match (goal) {
            DAOGoal::Secure => 0,
            DAOGoal::Loans => 1,
            DAOGoal::BNPL => 2,
        }
    }

    fun find_member_index(members: &vector<Member>, member_addr: address): u64 {
        let i = 0;
        let len = vector::length(members);

        while (i < len) {
            let member = vector::borrow(members, i);
            if (member.address == member_addr) {
                return i
            };
            i += 1;
        };

        len
    }

    fun recalculate_voting_power(members: &mut vector<Member>, total_investments: u64) {
        let i = 0;
        let len = vector::length(members);

        while (i < len) {
            let member = vector::borrow_mut(members, i);

            if (total_investments > 0) {
                member.voting_power_bps = (member.investment_amount * 10000) / total_investments;
            } else {
                member.voting_power_bps = 0;
            };

            i += 1;
        };
    }

    #[test_only]
    public fun init_module_for_test(sender: &signer) {
        init_module(sender);
    }
}
