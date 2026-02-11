use axum::{extract::State, Json};
use serde::{Deserialize, Serialize};

use crate::{app_state::AppState, error::AppError};

#[derive(Debug, Serialize, sqlx::FromRow)]
pub struct Student {
    pub id: i64,
    pub name: String,
    pub grade_level: Option<String>,
    pub created_at: String,
}

#[derive(Debug, Deserialize)]
pub struct CreateStudentRequest {
    pub name: String,
    pub grade_level: Option<String>,
}

pub async fn list_students(State(state): State<AppState>) -> Result<Json<Vec<Student>>, AppError> {
    let rows = sqlx::query_as::<_, Student>(
        "SELECT id, name, grade_level, created_at FROM students ORDER BY id ASC",
    )
    .fetch_all(&state.pool)
    .await?;

    Ok(Json(rows))
}

pub async fn create_student(
    State(state): State<AppState>,
    Json(payload): Json<CreateStudentRequest>,
) -> Result<Json<Student>, AppError> {
    if payload.name.trim().is_empty() {
        return Err(AppError::BadRequest("name is required".to_string()));
    }

    let created = sqlx::query_as::<_, Student>(
        r#"
        INSERT INTO students(name, grade_level)
        VALUES(?, ?)
        RETURNING id, name, grade_level, created_at
        "#,
    )
    .bind(payload.name.trim())
    .bind(payload.grade_level)
    .fetch_one(&state.pool)
    .await?;

    Ok(Json(created))
}
