use reqwest::Client;
use sqlx::SqlitePool;

use crate::config::Config;

#[derive(Clone)]
pub struct AppState {
    pub pool: SqlitePool,
    pub llm_client: Client,
    pub config: Config,
}
