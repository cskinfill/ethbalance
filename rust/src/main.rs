use std::sync::Arc;

use axum::{
    extract::{Path, State},
    http::StatusCode,
    routing::get,
    Json, Router,
};
use axum_prometheus::PrometheusMetricLayer;
use clap::Parser;
use metrics_process::Collector;
use reqwest::Client;
use serde_json::json;
use std::error::Error;
use tower::ServiceBuilder;
use tower_http::trace::TraceLayer;
use tracing::*;
use tracing_subscriber::fmt::format::FmtSpan;
use tracing_subscriber::EnvFilter;

#[derive(Parser, Debug)] // requires `derive` feature
#[command()] // Just to make testing across clap features easier
struct Args {
    #[clap(long, env)]
    api_key: String,
    #[arg(short = 'p')]
    port: Option<usize>,
}

#[derive(Clone)]
struct AppState {
    url: String,
    client: Client,
}

#[tokio::main]
#[instrument]
async fn main() -> Result<(), Box<dyn Error>> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .with_span_events(FmtSpan::CLOSE)
        .init();

    let args = Args::parse();

    let state = AppState {
        url: format!(
            "https://mainnet.infura.io/v3/{api_key}",
            api_key = args.api_key
        ),
        client: reqwest::Client::new(),
    };

    let (prometheus_layer, metric_handle) = PrometheusMetricLayer::pair();
    let collector = Collector::default();

    let app = Router::new()
        .route("/", get(root))
        .route("/address/transaction/:address", get(transaction))
        .route("/address/balance/:address", get(balance))
        .route(
            "/metrics",
            get(move || {
                collector.collect();
                std::future::ready(metric_handle.render())
            }),
        )
        .route_layer(
            ServiceBuilder::new()
                .layer(TraceLayer::new_for_http())
                .layer(prometheus_layer),
        )
        .with_state(Arc::new(state));

    let listener =
        tokio::net::TcpListener::bind(format!("0.0.0.0:{}", args.port.unwrap_or(3000))).await?;
    info!("App running on port {}", args.port.unwrap_or(3000));
    axum::serve(listener, app).await?;
    Ok(())
}

#[instrument]
#[axum::debug_handler]
async fn root() -> Result<Json<Vec<&'static str>>, StatusCode> {
    Ok(Json(vec!["/", "/address/balance/:address", "/metrics"]))
}

#[instrument(skip(app))]
#[axum::debug_handler]
async fn transaction(
    Path(address): Path<String>,
    State(app): State<Arc<AppState>>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    retrieve_trx(address, app)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)
        .map(Json)
}

#[instrument(skip(app))]
async fn retrieve_trx(
    address: String,
    app: Arc<AppState>,
) -> Result<serde_json::Value, reqwest::Error> {
    let body = json!({
    "jsonrpc": "2.0",
    "method": "eth_getTransactionByHash",
    "params": [
        address
    ],
    "id": 1
    });

    app.client
        .post(app.url.clone())
        .json(&body)
        .send()
        .await?
        .json::<serde_json::Value>()
        .await
        .inspect(|f| debug!("Response is {:?}", f))
}

#[derive(serde::Deserialize, serde::Serialize, Debug)]
struct BalanceResponse {
    balance: f64,
}

#[axum::debug_handler]
#[instrument(skip(app))]
async fn balance(
    Path(address): Path<String>,
    State(app): State<Arc<AppState>>,
) -> Result<Json<BalanceResponse>, StatusCode> {
    retrieve_balance(address, app)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)
        .map(|b| b.result)
        .inspect(|b| debug!("pre-parsed balance is {b}"))
        .map(|b| b.trim_start_matches("0x").to_string())
        .and_then(|b| u64::from_str_radix(&b, 16).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR))
        .inspect(|b| debug!("parsed balance is {b}"))
        .map(|b| (b as f64) * 1e-18)
        .map(|b| BalanceResponse { balance: b })
        .map(Json)
}

#[derive(serde::Deserialize, Debug)]
struct Balance {
    // id: serde_json::Number,
    // jsonrpc: String,
    result: String,
}

#[instrument(skip(app))]
async fn retrieve_balance(address: String, app: Arc<AppState>) -> Result<Balance, reqwest::Error> {
    let body = json!({
    "jsonrpc": "2.0",
    "method": "eth_getBalance",
    "params": [
        address,
        "latest"
    ],
    "id": 1
    });
    let resp = app
        .client
        .post(app.url.clone())
        .json(&body)
        .send()
        .await?
        .json::<Balance>()
        .await;
    debug!("Response is {:?}", resp);
    resp
}
