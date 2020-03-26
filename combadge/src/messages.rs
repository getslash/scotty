use std::string::ToString;

#[derive(Debug)]
pub enum ClientMessages {
    BeamComplete = 0,
    StartBeamingFile = 1,
    FileChunk = 2,
    FileDone = 3,
    ProtocolVersion = 4,
}

#[derive(Debug)]
pub enum ServerMessages {
    SkipFile = 0,
    BeamFile = 1,
    FileBeamed = 2,
}

impl ServerMessages {
    pub fn from_u8(code: u8) -> ServerMessages {
        match code {
            0 => ServerMessages::SkipFile,
            1 => ServerMessages::BeamFile,
            2 => ServerMessages::FileBeamed,
            _ => panic!(),
        }
    }
}

impl ToString for ServerMessages {
    fn to_string(&self) -> String {
        match *self {
            ServerMessages::SkipFile => "SkipFile",
            ServerMessages::BeamFile => "BeamFile",
            ServerMessages::FileBeamed => "FileBeamed",
        }
        .to_string()
    }
}
