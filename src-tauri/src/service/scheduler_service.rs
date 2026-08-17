use crate::model::account::Account;

pub fn retry_limit(configured: u32) -> u32 {
    configured.clamp(1, 20)
}
pub fn sort_key(account: &Account) -> (i64, std::cmp::Reverse<String>) {
    (
        account.priority,
        std::cmp::Reverse(account.name.to_lowercase()),
    )
}
