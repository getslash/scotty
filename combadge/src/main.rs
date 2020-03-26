extern crate byteorder;
extern crate env_logger;
extern crate flate2;
extern crate log;
extern crate structopt;
extern crate walkdir;

mod config;
mod messages;

use self::config::Config;
use self::messages::{ClientMessages, ServerMessages};
use byteorder::{ReadBytesExt, WriteBytesExt};
use flate2::write::GzEncoder;
use flate2::Compression;
use log::{debug, error, trace, warn};
use std::ffi::OsStr;
use std::fs::{self, File};
use std::io::{prelude::*, Write};
use std::net::TcpStream;
use std::path::Path;
use std::time::SystemTime;
use structopt::StructOpt;
use walkdir::WalkDir;

const CHUNK_SIZE: usize = 1024 * 128;

fn main() -> std::io::Result<()> {
    env_logger::init();
    let config = Config::from_args();
    debug!("Started beaming up with {:?}", config);
    match beam_up(config) {
        Err(e) => error!("Failed to beam up: {:?}", e.to_string()),
        _ => debug!("Finished"),
    }
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

    beam_path(&mut transporter, path)?;

    transporter.write_u8(ClientMessages::BeamComplete as u8)?;

    Ok(())
}

fn beam_path(transporter: &mut TcpStream, path: &Path) -> std::io::Result<()> {
    if !path.exists() {
        return Ok(());
    } else if path.is_file() {
        beam_file(transporter, path.parent(), &path)?;
    } else if path.is_dir() {
        trace!("Path is a directory: {:?}", path);
        for entry in WalkDir::new(path)
            .follow_links(false)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            trace!("Entry: {:?}", entry);
            if entry.path().is_file() {
                beam_file(transporter, Some(&path), &entry.path())?;
            }
        }
    } else {
        warn!("Path is not a file: {:?}", path);
    }

    Ok(())
}

fn should_compress_file(path: &Path) -> bool {
    match path.extension().and_then(OsStr::to_str) {
        Some("zip") | Some("gz") | Some("bz2") | Some("xz") | Some("zst") | Some("tgz")
        | Some("tbz2") | Some("txz") | Some("ioym") | Some("br") => false,
        _ => true,
    }
}

fn get_textual_path(path: &Path, base_path: Option<&Path>, should_compress: bool) -> String {
    let path_without_base = match base_path {
        Some(base_path) => path
            .strip_prefix(base_path)
            .map(|p| Path::new(".").join(p))
            .unwrap_or_else(|_| path.to_path_buf()),
        None => path.to_path_buf(),
    };
    let mut textual_path = path_without_base.to_string_lossy().into_owned();
    if should_compress {
        textual_path.push_str(".gz");
    }
    textual_path
}

fn beam_file(
    transporter: &mut TcpStream,
    base_path: Option<&Path>,
    path: &Path,
) -> std::io::Result<()> {
    debug!("Beaming file: {:?}", path);

    transporter.write_u8(ClientMessages::StartBeamingFile as u8)?;
    let should_compress = should_compress_file(&path);
    let textual_path = get_textual_path(&path, base_path, should_compress);
    let path_as_bytes = textual_path.as_bytes();
    transporter.write_u16::<byteorder::BigEndian>(path_as_bytes.len() as u16)?;
    transporter.write_all(path_as_bytes)?;
    trace!("Beam path: {:?}", textual_path);

    let answer = transporter.read_u8().map(ServerMessages::from_u8)?;
    match answer {
        ServerMessages::BeamFile => {
            debug!("Server asks us to beam this file");
        }
        ServerMessages::SkipFile => {
            warn!("Server asks us to skip this file");
            return Ok(());
        }
        _ => panic!("Unexpected server response: {:?}", answer),
    };

    let duration = fs::metadata(path)?
        .modified()?
        .duration_since(SystemTime::UNIX_EPOCH);
    transporter.write_u64::<byteorder::BigEndian>(duration.unwrap().as_secs())?;

    let mut encoder = if should_compress {
        Some(GzEncoder::new(
            Vec::with_capacity(CHUNK_SIZE),
            Compression::best(),
        ))
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
            debug!("Server reports that the file was beamed");
        }
        _ => panic!("Unexpected server response: {:?}", message_code),
    };

    Ok(())
}

#[cfg(unix)]
#[cfg(test)]
mod test_unix {
    use super::*;

    #[test]
    fn test_get_textual_path_simple() {
        assert_eq!(
            get_textual_path(Path::new("/tmp/a.log"), Some(Path::new("/tmp")), false),
            "./a.log"
        )
    }

    #[test]
    fn test_get_textual_path_compression() {
        assert_eq!(
            get_textual_path(Path::new("/tmp/a.log"), Some(Path::new("/tmp")), true),
            "./a.log.gz"
        )
    }

    #[test]
    fn test_get_textual_path_no_base_path() {
        assert_eq!(
            get_textual_path(Path::new("/tmp/a.log"), None, false),
            "/tmp/a.log"
        )
    }

    #[test]
    fn test_get_textual_path_bad_base_path() {
        assert_eq!(
            get_textual_path(
                Path::new("/tmp/a.log"),
                Some(Path::new("/unrelated")),
                false
            ),
            "/tmp/a.log"
        )
    }

    #[test]
    fn test_get_textual_path_no_base_path_compression() {
        assert_eq!(
            get_textual_path(Path::new("/tmp/a.log"), None, true),
            "/tmp/a.log.gz"
        )
    }

    #[test]
    fn test_get_textual_path_subdir() {
        assert_eq!(
            get_textual_path(Path::new("/tmp/a/b.log"), Some(Path::new("/tmp")), false),
            "./a/b.log"
        )
    }

    #[test]
    fn test_get_textual_path_base_path_has_subdir() {
        assert_eq!(
            get_textual_path(Path::new("/tmp/a/b.log"), Some(Path::new("/tmp/a")), false),
            "./b.log"
        )
    }

    #[test]
    fn test_should_compress_file() {
        assert!(should_compress_file(Path::new("/tmp/a.log")))
    }

    #[test]
    fn test_should_not_compress_file() {
        assert!(!should_compress_file(Path::new("/tmp/a.ioym")))
    }
}

#[cfg(windows)]
#[cfg(test)]
mod test_windows {
    use super::*;

    #[test]
    fn test_get_textual_path_simple() {
        assert_eq!(
            get_textual_path(Path::new("C:\\a.log"), Some(Path::new("C:\\")), false),
            ".\\a.log"
        )
    }

    #[test]
    fn test_get_textual_path_compression() {
        assert_eq!(
            get_textual_path(Path::new("C:\\a.log"), Some(Path::new("C:\\")), true),
            ".\\a.log.gz"
        )
    }

    #[test]
    fn test_get_textual_path_no_base_path() {
        assert_eq!(
            get_textual_path(Path::new("C:\\a.log"), None, false),
            "C:\\a.log"
        )
    }

    #[test]
    fn test_get_textual_path_no_base_path_compression() {
        assert_eq!(
            get_textual_path(Path::new("C:\\a.log"), None, true),
            "C:\\a.log.gz"
        )
    }

    #[test]
    fn test_get_textual_path_subdir() {
        assert_eq!(
            get_textual_path(Path::new("C:\\a\\b.log"), Some(Path::new("C:\\")), false),
            ".\\a\\b.log"
        )
    }

    #[test]
    fn test_get_textual_path_base_path_has_subdir() {
        assert_eq!(
            get_textual_path(Path::new("C:\\a\\b.log"), Some(Path::new("C:\\a")), false),
            ".\\b.log"
        )
    }

    #[test]
    fn test_should_compress_file() {
        assert!(should_compress_file(Path::new("C:\\a.log")))
    }

    #[test]
    fn test_should_not_compress_file() {
        assert!(!should_compress_file(Path::new("C:\\a.ioym")))
    }
}
