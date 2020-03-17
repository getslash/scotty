mod beam;
mod error;
mod scotty;
mod server;
mod storage;

extern crate byteorder;
extern crate clap;
extern crate crypto;
extern crate fern;
#[macro_use]
extern crate log;
extern crate openssl_probe;
#[macro_use]
extern crate quick_error;
extern crate reqwest;
extern crate sentry;
extern crate serde;
#[macro_use]
extern crate serde_derive;
extern crate serde_json;
extern crate time;
extern crate url;

use clap::{App, Arg};
use storage::FileStorage;

const VERSION: &'static str = env!("CARGO_PKG_VERSION");

pub type BeamId = usize;
pub type Mtime = u64;

fn main() {
    let matches = App::new("Transporter")
        .version(VERSION)
        .about("Scotty's transporter server")
        .arg(
            Arg::with_name("storage_path")
                .help("Path to the storage directory")
                .required(true)
                .long("storage")
                .env("TRANSPORTER_STORAGE_PATH"),
        )
        .arg(
            Arg::with_name("bind_address")
                .help("Bind address")
                .default_value("0.0.0.0:9000")
                .long("bind")
                .env("TRANSPORTER_BIND_ADDRESS"),
        )
        .arg(
            Arg::with_name("sentry_dsn")
                .help("Sentry DSN")
                .long("sentry-dsn")
                .env("TRANSPORTER_SENTRY_DSN"),
        )
        .arg(
            Arg::with_name("scotty_url")
                .help("Scotty URL")
                .long("scotty-url")
                .required(true)
                .env("TRANSPORTER_SCOTTY_URL"),
        )
        .get_matches();

    openssl_probe::init_ssl_cert_env_vars();

    fern::Dispatch::new()
        .format(|out, message, record| {
            out.finish(format_args!(
                "[{}] {}",
                record.module_path().unwrap_or(""),
                message
            ))
        })
        .level(log::LevelFilter::Trace)
        .chain(std::io::stdout())
        .apply()
        .unwrap();

    let storage = match FileStorage::open(matches.value_of("storage_path").unwrap()) {
        Ok(s) => s,
        Err(why) => panic!("Cannot open storage: {}", why),
    };

    let _guard = matches.value_of("sentry_dsn").map(|dsn| sentry::init(dsn));

    match server::listen(
        storage,
        matches.value_of("bind_address").unwrap(),
        matches.value_of("scotty_url").unwrap(),
    ) {
        Err(why) => panic!("Server crashed: {}", why),
        _ => (),
    }
}
