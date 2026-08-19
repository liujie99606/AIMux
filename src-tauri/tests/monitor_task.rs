use std::cmp::Ordering;

use aimux_lib::background::monitor_task::{candidate_order, should_promote};

#[test]
fn chooses_the_lowest_multiplier_then_the_fastest_average_duration() {
    assert_eq!(
        candidate_order(0.04, Some(900), 0.10, Some(100)),
        Ordering::Less
    );
    assert_eq!(
        candidate_order(0.10, Some(500), 0.10, Some(800)),
        Ordering::Less
    );
    assert_eq!(candidate_order(0.10, Some(500), 0.10, None), Ordering::Less);
    assert_eq!(
        candidate_order(0.10, None, 0.10, Some(500)),
        Ordering::Greater
    );
}

#[test]
fn promotes_a_successful_lower_multiplier_account() {
    assert!(should_promote(0.04, None, 0.10, Some(500)));
}

#[test]
fn promotes_a_faster_account_when_multipliers_match() {
    assert!(should_promote(0.10, Some(500), 0.10, Some(800)));
    assert!(should_promote(0.10, Some(500), 0.10, None));
}

#[test]
fn does_not_promote_an_unknown_or_slower_account_when_multipliers_match() {
    assert!(!should_promote(0.10, None, 0.10, Some(800)));
    assert!(!should_promote(0.10, None, 0.10, None));
    assert!(!should_promote(0.10, Some(800), 0.10, Some(500)));
}
