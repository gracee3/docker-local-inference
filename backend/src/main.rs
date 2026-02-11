mod app_state;
mod config;
mod db;
mod error;
mod routes;

use std::net::SocketAddr;

use axum::{
    routing::{get, post},
    Router,
};
use config::Config;
use routes::{
    health::healthz,
    llm::proxy_chat_completion,
    students::{create_student, list_students},
};
use tokio::net::TcpListener;
use tower_http::{cors::CorsLayer, trace::TraceLayer};
use tracing::info;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    let cfg = Config::from_env()?;
    let state = db::build_state(cfg).await?;

    let addr: SocketAddr =
        format!("{}:{}", state.config.app_host, state.config.app_port).parse()?;

    let app = Router::new()
        .route("/healthz", get(healthz))
        .route("/students", get(list_students).post(create_student))
        .route("/llm/chat", post(proxy_chat_completion))
        .with_state(state)
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http());
    let listener = TcpListener::bind(addr).await?;

    info!(%addr, "backend listening");
    axum::serve(listener, app).await?;

    Ok(())
}
