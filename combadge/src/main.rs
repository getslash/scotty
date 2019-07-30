extern crate byteorder;
extern crate structopt;
extern crate zstd;

mod config;
mod messages;

use self::config::Config;
use self::messages::{ClientMessages, ServerMessages};
use byteorder::{ReadBytesExt, WriteBytesExt};
use std::ffi::OsStr;
use std::fs::{self, File};
use std::io::{prelude::*, Write};
use std::net::TcpStream;
use std::path::Path;
use std::time::SystemTime;
use structopt::StructOpt;

const CHUNK_SIZE: usize = 1024 * 128;

fn main() -> std::io::Result<()> {
    let config = Config::from_args();
    println!("Started");
    beam_up(config)?;
    println!("Finished");
    Ok(())
}

fn beam_up(config: Config) -> std::io::Result<()> {
    let beam_id = config.beam_id;

    // CR: I'm not sure this is necessary
    let path = Path::new(&config.path);

    let mut transporter = TcpStream::connect((config.transporter_addr.as_str(), 9000))?;

    transporter.write_u64::<byteorder::BigEndian>(beam_id)?;
    transporter.write_u8(ClientMessages::ProtocolVersion as u8)?;
    transporter.write_u16::<byteorder::BigEndian>(2)?;

    beam_path(&mut transporter, path, beam_id)?;

    transporter.write_u8(ClientMessages::BeamComplete as u8)?;

    Ok(())
}

fn beam_path(transporter: &mut TcpStream, path: &Path, beam_id: u64) -> std::io::Result<()> {
    if !path.exists() {
        return Ok(())
    } else if path.is_file() {
        beam_file(transporter, &path)?;
    } else if path.is_dir() {
        for entry in fs::read_dir(path)? {
            beam_path(transporter, &entry?.path(), beam_id)?;
        }
    } else {
        panic!("Error with path: {:?}", path);
    }

    Ok(())
}

fn beam_file(transporter: &mut TcpStream, path: &Path) -> std::io::Result<()> {
    let should_compress = match path.extension().and_then(OsStr::to_str) {
        Some("zip") | Some("gz") | Some("bz2") | Some("xz") | Some("zst") | Some("tgz")
        | Some("tbz2") | Some("txz") | Some("ioym") | Some("br") => false,
        _ => true,
    };

    transporter.write_u8(ClientMessages::StartBeamingFile as u8)?;

    let mut textual_path = path.to_string_lossy().into_owned();
    if should_compress {
        textual_path.push_str(".zst");
    }

    let path_as_bytes = textual_path.as_bytes();
    transporter.write_u16::<byteorder::BigEndian>(path_as_bytes.len() as u16)?;
    transporter.write_all(path_as_bytes)?;
    println!("Beam path: {:?}", textual_path);

    let answer = transporter.read_u8().map(ServerMessages::from_u8)?;
    match answer {
        ServerMessages::BeamFile => {
            println!("Server asks us to beam this file");
        }
        ServerMessages::SkipFile => {
            println!("Server asks us to skip this file");
            return Ok(());
        }
        _ => panic!("Unexpected server response: {:?}", answer),
    };

    let duration = fs::metadata(path)?
        .modified()?
        .duration_since(SystemTime::UNIX_EPOCH);
    transporter.write_u64::<byteorder::BigEndian>(duration.unwrap().as_secs())?;

    let mut encoder = if should_compress {
        Some(zstd::stream::write::Encoder::new(Vec::with_capacity(CHUNK_SIZE), 6).unwrap())
    } else {
        None
    };

    let mut file = File::open(path)?;
    let mut buffer = [0u8; CHUNK_SIZE];
    loop {
        let read_size = file.read(&mut buffer)?;
        if read_size == 0 {
            break;
        }

        let buffer = &buffer[..read_size];

        if let Some(encoder) = &mut encoder {
            encoder.get_mut().clear();
            encoder.write_all(buffer).unwrap();
        }

        let to_send: &[u8] = encoder.as_ref().map(|e| &e.get_ref()[..]).unwrap_or(buffer);

        transporter.write_u8(ClientMessages::FileChunk as u8)?;
        transporter.write_u32::<byteorder::BigEndian>(to_send.len() as u32)?;
        transporter.write_all(to_send)?;
    }
    drop(buffer);

    if let Some(mut encoder) = encoder {
        encoder.get_mut().clear();
        let to_send = encoder.finish().unwrap();

        transporter.write_u8(ClientMessages::FileChunk as u8)?;
        transporter.write_u32::<byteorder::BigEndian>(to_send.len() as u32)?;
        transporter.write_all(&to_send)?;
    }

    transporter.write_u8(ClientMessages::FileDone as u8)?;

    let message_code = transporter.read_u8().map(ServerMessages::from_u8)?;
    match message_code {
        ServerMessages::FileBeamed => {
            println!("Server reports that the file was beamed");
        }
        _ => panic!("Unexpected server response: {:?}", message_code),
    };

    Ok(())
}
