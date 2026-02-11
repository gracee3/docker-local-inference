use axum::{extract::State, Json};
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::{app_state::AppState, error::AppError};

#[derive(Debug, Deserialize)]
pub struct LlmProxyRequest {
    pub user_id: Option<i64>,
    pub student_id: Option<i64>,
    pub payload: Value,
}

#[derive(Debug, Serialize)]
pub struct LlmProxyResponse {
    pub upstream: Value,
}

pub async fn proxy_chat_completion(
    State(state): State<AppState>,
    Json(body): Json<LlmProxyRequest>,
) -> Result<Json<LlmProxyResponse>, AppError> {
    if !body.payload.is_object() {
        return Err(AppError::BadRequest(
            "payload must be a JSON object".to_string(),
        ));
    }

    let url = format!(
        "{}{}",
        state.config.llm_base_url.trim_end_matches('/'),
        state.config.llm_chat_path
    );

    let response = state
        .llm_client
        .post(url)
        .json(&body.payload)
        .send()
        .await?;

    let status = response.status();
    let upstream_json: Value = response.json().await?;

    if !status.is_success() {
        return Err(AppError::Upstream(upstream_json.to_string()));
    }

    let prompt_text = body
        .payload
        .get("messages")
        .map(ToString::to_string)
        .unwrap_or_else(|| body.payload.to_string());

    let response_text = upstream_json.to_string();

    sqlx::query(
        r#"
        INSERT INTO ai_interactions (user_id, student_id, prompt, response)
        VALUES (?, ?, ?, ?)
        "#,
    )
    .bind(body.user_id)
    .bind(body.student_id)
    .bind(prompt_text)
    .bind(response_text)
    .execute(&state.pool)
    .await?;

    Ok(Json(LlmProxyResponse {
        upstream: upstream_json,
    }))
}
