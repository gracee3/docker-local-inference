use std::{path::Path, str::FromStr};

use reqwest::Client;
use sqlx::{
    sqlite::{SqliteConnectOptions, SqliteJournalMode, SqlitePoolOptions, SqliteSynchronous},
    Executor,
};

use crate::{app_state::AppState, config::Config};

pub async fn build_state(cfg: Config) -> Result<AppState, Box<dyn std::error::Error>> {
    ensure_sqlite_parent_dir(&cfg.database_url)?;

    let opts = SqliteConnectOptions::from_str(&cfg.database_url)?
        .create_if_missing(true)
        .journal_mode(SqliteJournalMode::Wal)
        .synchronous(SqliteSynchronous::Normal)
        .foreign_keys(true);

    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect_with(opts)
        .await?;

    // Startup pragmas keep defaults explicit if settings are changed by external tooling.
    pool.execute("PRAGMA journal_mode=WAL;").await?;
    pool.execute("PRAGMA synchronous=NORMAL;").await?;
    pool.execute("PRAGMA foreign_keys=ON;").await?;

    sqlx::migrate!("./migrations").run(&pool).await?;

    let llm_client = Client::builder()
        .timeout(std::time::Duration::from_secs(90))
        .build()?;

    Ok(AppState {
        pool,
        llm_client,
        config: cfg,
    })
}

fn ensure_sqlite_parent_dir(database_url: &str) -> Result<(), Box<dyn std::error::Error>> {
    const PREFIX: &str = "sqlite://";

    if let Some(rest) = database_url.strip_prefix(PREFIX) {
        let file_part = rest.split('?').next().unwrap_or(rest);

        if file_part != ":memory:" && !file_part.is_empty() {
            let path = Path::new(file_part);
            if let Some(parent) = path.parent() {
                if !parent.as_os_str().is_empty() {
                    std::fs::create_dir_all(parent)?;
                }
            }
        }
    }

    Ok(())
}
