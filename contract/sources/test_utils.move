#[test_only]
module optimus::test_utils {
    use aptos_framework::timestamp;
    use aptos_framework::account;
    use std::signer;

    public fun init_test_env(aptos_framework: &signer) {
        timestamp::set_time_has_started_for_testing(aptos_framework);
    }

    public fun create_test_account(addr: address) {
        account::create_account_for_test(addr);
    }

    public fun set_timestamp(_aptos_framework: &signer, timestamp_secs: u64) {
        timestamp::update_global_time_for_test_secs(timestamp_secs);
    }

    public fun advance_time(_aptos_framework: &signer, seconds: u64) {
        let current = timestamp::now_seconds();
        timestamp::update_global_time_for_test_secs(current + seconds);
    }

    public fun get_current_timestamp(): u64 {
        timestamp::now_seconds()
    }

    public fun signer_address(signer_ref: &signer): address {
        signer::address_of(signer_ref)
    }
}
