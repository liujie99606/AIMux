use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SettingValue {
    pub key: String,
    pub value: String,
}
