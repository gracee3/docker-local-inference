use std::env;

#[derive(Clone, Debug)]
pub struct Config {
    pub app_host: String,
    pub app_port: u16,
    pub database_url: String,
    pub llm_base_url: String,
    pub llm_chat_path: String,
}

impl Config {
    pub fn from_env() -> Result<Self, Box<dyn std::error::Error>> {
        let app_host = env::var("APP_HOST").unwrap_or_else(|_| "127.0.0.1".to_string());
        let app_port = env::var("APP_PORT")
            .unwrap_or_else(|_| "3000".to_string())
            .parse::<u16>()?;
        let database_url =
            env::var("DATABASE_URL").unwrap_or_else(|_| "sqlite://data/app.db".to_string());
        let llm_base_url =
            env::var("LLM_BASE_URL").unwrap_or_else(|_| "http://127.0.0.1:8000".to_string());
        let llm_chat_path =
            env::var("LLM_CHAT_PATH").unwrap_or_else(|_| "/v1/chat/completions".to_string());

        Ok(Self {
            app_host,
            app_port,
            database_url,
            llm_base_url,
            llm_chat_path,
        })
    }
}
