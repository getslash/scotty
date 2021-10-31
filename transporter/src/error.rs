use super::beam::ClientMessages;
use super::scotty::ScottyError;
use std::convert::From;
use std::io::Error as IoError;

quick_error! {
    #[derive(Debug)]
    pub enum TransporterError {
        InvalidClientMessageCode(msg: u8) {
            display("Invalid message code: {}", msg)
        }
        InvalidProtocolVersion(protocol: u16) {
            display("Invalid protocol version: {}", protocol)
        }
        UnexpectedClientMessageCode(code: ClientMessages) {
            display("Unexpected message code: {:?}", code)
        }
        ScottyError(err: ScottyError) {
            from()
            display("Scotty error: {}", err)
        }
        ClientEOF {
            display("Client close the connection in a middle of a beam")
        }
        ClientIoError(err: IoError) {
            display("Client IO error: {}", err)
        }
        StorageIoError(err: IoError) {
            display("Storage IO error: {}", err)
        }
    }
}

impl TransporterError {
    pub fn is_disconnection(&self) -> bool {
        matches!(
            *self,
            TransporterError::ClientIoError(_) | TransporterError::ClientEOF
        )
    }
}

pub type TransporterResult<T> = Result<T, TransporterError>;
