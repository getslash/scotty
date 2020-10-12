use super::error::{TransporterError, TransporterResult};
use super::scotty::Scotty;
use super::storage::FileStorage;
use super::Mtime;
use byteorder::{BigEndian, ReadBytesExt, WriteBytesExt};
use crypto::digest::Digest;
use crypto::sha2::Sha512;
use std::cmp::min;
use std::io::{Read, Write};
use std::net::TcpStream;

const CHUNK_SIZE: usize = 1_048_576_usize;

#[derive(Debug)]
pub enum ClientMessages {
    BeamComplete,
    StartBeamingFile,
    FileChunk,
    FileDone,
    ProtocolVersion,
}

impl ClientMessages {
    fn from_u8(code: u8) -> TransporterResult<ClientMessages> {
        match code {
            0 => Ok(ClientMessages::BeamComplete),
            1 => Ok(ClientMessages::StartBeamingFile),
            2 => Ok(ClientMessages::FileChunk),
            3 => Ok(ClientMessages::FileDone),
            4 => Ok(ClientMessages::ProtocolVersion),
            _ => Err(TransporterError::InvalidClientMessageCode(code)),
        }
    }
}

#[derive(Debug)]
enum ProtocolVersion {
    V1,
    V2,
}

impl ProtocolVersion {
    fn from_u16(code: u16) -> TransporterResult<ProtocolVersion> {
        match code {
            1 => Ok(ProtocolVersion::V1),
            2 => Ok(ProtocolVersion::V2),
            _ => Err(TransporterError::InvalidProtocolVersion(code)),
        }
    }

    fn supports_mtime(&self) -> bool {
        !matches!(*self, ProtocolVersion::V1)
    }
}

enum ServerMessages {
    SkipFile = 0,
    BeamFile = 1,
    FileBeamed = 2,
}

type FileData = (usize, Sha512, Option<Mtime>);

fn read_file_name(stream: &mut TcpStream) -> TransporterResult<String> {
    let file_name_length = stream
        .read_u16::<BigEndian>()
        .map_err(TransporterError::ClientIoError)? as usize;
    let mut file_name = String::new();
    let file_name_length_read = stream
        .take(file_name_length as u64)
        .read_to_string(&mut file_name)
        .map_err(TransporterError::ClientIoError)?;
    assert_eq!(file_name_length_read, file_name_length);
    Ok(file_name)
}

fn download(
    stream: &mut TcpStream,
    storage: &FileStorage,
    file_id: &str,
    protocol_version: &ProtocolVersion,
) -> TransporterResult<FileData> {
    let mut file = storage.create(file_id)?;
    let mut checksum = Sha512::new();
    let mut length: usize = 0;
    let mut read_chunk = [0u8; CHUNK_SIZE];

    let mtime = if protocol_version.supports_mtime() {
        Some(
            stream
                .read_u64::<BigEndian>()
                .map_err(TransporterError::ClientIoError)?,
        )
    } else {
        None
    };

    loop {
        let message_code = stream
            .read_u8()
            .map_err(TransporterError::ClientIoError)
            .and_then(ClientMessages::from_u8)?;
        match message_code {
            ClientMessages::FileChunk => (),
            ClientMessages::FileDone => return Ok((length, checksum, mtime)),
            _ => return Err(TransporterError::UnexpectedClientMessageCode(message_code)),
        }

        let chunk_size = stream
            .read_u32::<BigEndian>()
            .map_err(TransporterError::ClientIoError)?;
        let mut bytes_remaining = chunk_size as usize;
        while bytes_remaining > 0 {
            let to_read = min(bytes_remaining, read_chunk.len());
            let bytes_read = stream
                .read(&mut read_chunk[0..to_read])
                .map_err(TransporterError::ClientIoError)?;
            if bytes_read == 0 {
                return Err(TransporterError::ClientEOF);
            }
            checksum.input(&read_chunk[0..bytes_read]);
            file.write_all(&read_chunk[0..bytes_read])
                .map_err(TransporterError::StorageIoError)?;
            bytes_remaining -= bytes_read;
            length += bytes_read;
        }
    }
}

fn beam_file(
    beam_id: usize,
    stream: &mut TcpStream,
    storage: &FileStorage,
    scotty: &mut Scotty,
    protocol_version: &ProtocolVersion,
) -> TransporterResult<()> {
    debug!("{}: Got a request to beam up file", beam_id);
    let file_name = read_file_name(stream)?;
    debug!("{}: File name is {}", beam_id, file_name);

    let (file_id, storage_name, should_beam) = scotty.file_beam_start(beam_id, &file_name)?;
    debug!("{}: ID of {} is {}.", beam_id, file_name, file_id);

    if !should_beam {
        debug!(
            "{}: Notifying the client that we should'nt beam {}.",
            beam_id, file_id
        );
        stream
            .write_u8(ServerMessages::SkipFile as u8)
            .map_err(TransporterError::ClientIoError)?;
        return Ok(());
    }

    debug!(
        "{}: Notifying the client that we should beam {}.",
        beam_id, file_id
    );
    stream
        .write_u8(ServerMessages::BeamFile as u8)
        .map_err(TransporterError::ClientIoError)?;

    info!("{}: Beaming up {} to {}", beam_id, file_name, storage_name);

    match download(stream, storage, &storage_name, protocol_version) {
        Ok(data) => {
            let (length, mut checksum, mtime) = data;
            info!("Finished beaming up {} ({} bytes)", file_name, length);
            scotty.file_beam_end(
                &file_id,
                None,
                Some(length),
                Some(checksum.result_str()),
                mtime,
            )?;
            stream
                .write_u8(ServerMessages::FileBeamed as u8)
                .map_err(TransporterError::ClientIoError)?;
            Ok(())
        }
        Err(why) => {
            info!("Error beaming up {}: {}", file_name, why);
            scotty.file_beam_end(
                &file_id,
                Some(format!("{:?}", why).as_str()),
                None,
                None,
                None,
            )?;
            Err(why)
        }
    }
}

fn beam_loop(
    beam_id: usize,
    stream: &mut TcpStream,
    storage: &FileStorage,
    scotty: &mut Scotty,
) -> TransporterResult<()> {
    let mut protocol_version = ProtocolVersion::V1;
    loop {
        let message_code =
            ClientMessages::from_u8(stream.read_u8().map_err(TransporterError::ClientIoError)?)?;
        match message_code {
            ClientMessages::StartBeamingFile => {
                beam_file(beam_id, stream, storage, scotty, &protocol_version)?
            }
            ClientMessages::BeamComplete => return Ok(()),
            ClientMessages::ProtocolVersion => {
                protocol_version = stream
                    .read_u16::<BigEndian>()
                    .map_err(TransporterError::ClientIoError)
                    .and_then(ProtocolVersion::from_u16)?;
                info!("Client set the protocol version to {:?}", protocol_version);
            }
            _ => return Err(TransporterError::UnexpectedClientMessageCode(message_code)),
        }
    }
}

pub fn beam_up(
    mut stream: TcpStream,
    storage: FileStorage,
    mut scotty: Scotty,
    error_tags: &mut Vec<(String, String)>,
) -> TransporterResult<()> {
    let beam_id = stream
        .read_u64::<BigEndian>()
        .map_err(TransporterError::ClientIoError)? as usize;
    error_tags.push(("beam_id".to_string(), format!("{}", beam_id)));
    info!("Received beam up request with beam id {}", beam_id);

    match beam_loop(beam_id, &mut stream, &storage, &mut scotty) {
        Ok(_) => {
            info!("Beam up completed");
            scotty.complete_beam(beam_id, None)?;
            Ok(())
        }
        Err(why) => {
            error!("Beam up failed: {}", why);
            let error = format!("Transporter Error: {}", why);
            scotty.complete_beam(beam_id, Some(&error))?;
            Err(why)
        }
    }
}
