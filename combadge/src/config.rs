extern crate structopt;

use std::path::PathBuf;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
#[structopt(
    name = "combadge_config",
    about = "The configuration parameters for combadge."
)]
pub struct Config {
    #[structopt(short = "bi", long = "beam_id")]
    pub beam_id: u64,
    #[structopt(short = "p", long = "path", parse(from_os_str))]
    pub path: PathBuf,
    #[structopt(short = "ta", long = "transporter_addr")]
    pub transporter_addr: String,
}
