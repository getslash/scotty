#[allow(clippy::enum_variant_names)]

use super::{BeamId, Mtime};
use reqwest::Error as HttpError;
use reqwest::{Client, Method, Response, StatusCode};
use serde::ser::Serialize;
use serde_json;
use std::io::Error as IoError;
use std::thread::sleep;
use std::time::Duration;

const TIME_TO_SLEEP: u64 = 5;
const MAX_ATTEMPTS: u64 = 60000 / TIME_TO_SLEEP;

pub struct Scotty {
    url: String,
    client: Client,
}

#[derive(Deserialize)]
struct FilePostResponse {
    file_id: String,
    storage_name: String,
    should_beam: bool,
}

#[derive(Serialize)]
struct FilePostRequest {
    file_name: String,
    beam_id: BeamId,
}

#[derive(Serialize)]
struct FileUpdateRequest {
    success: bool,
    error: String,
    size: Option<usize>,
    mtime: Option<Mtime>,
    checksum: Option<String>,
}

#[derive(Serialize)]
struct BeamUpdateDocument<'a> {
    completed: bool,
    error: Option<&'a str>,
}

#[derive(Serialize)]
struct BeamUpdateRequest<'a> {
    beam: BeamUpdateDocument<'a>,
}

impl<'a> BeamUpdateRequest<'a> {
    fn new(completed: bool, error: Option<&'a str>) -> BeamUpdateRequest<'a> {
        BeamUpdateRequest {
            beam: BeamUpdateDocument { completed, error },
        }
    }
}

quick_error! {
    #[derive(Debug)]
    pub enum ScottyError {
        SerdeError(err: serde_json::Error) {
            from()
            display("Serde Error: {}", err)
        }
        HttpError(err: HttpError) {
            from()
            display("HTTP Error: {}", err)
        }
        ScottyError(code: StatusCode, url: String) {
            display("Scotty returned {} for {}", code, url)
        }
        ScottyIsDown {}
        IoError(err: IoError) {
            from()
            display("IO Error: {}", err)
        }
    }
}

pub type ScottyResult<T> = Result<T, ScottyError>;

impl Scotty {
    pub fn new(url: String) -> Scotty {
        Scotty {
            url,
            client: Client::new(),
        }
    }

    fn send_request<REQUEST: Serialize + Sized>(
        &self,
        method: Method,
        url: String,
        json: REQUEST,
    ) -> ScottyResult<Response> {
        for attempt in 0..MAX_ATTEMPTS {
            let response = self
                .client
                .request(method.clone(), &url)
                .json(&json)
                .send()?;

            let status_code = response.status();
            match status_code {
                StatusCode::OK => {
                    return Ok(response);
                }
                StatusCode::BAD_GATEWAY | StatusCode::GATEWAY_TIMEOUT => {
                    error!(
                        "Scotty returned {}. Attempt {} out of {}",
                        status_code,
                        attempt + 1,
                        MAX_ATTEMPTS
                    );
                    sleep(Duration::from_secs(TIME_TO_SLEEP));
                }
                _ => {
                    return Err(ScottyError::ScottyError(status_code, url));
                }
            }
        }
        Err(ScottyError::ScottyIsDown)
    }

    pub fn file_beam_start(
        &mut self,
        beam_id: BeamId,
        file_name: &str,
    ) -> ScottyResult<(String, String, bool)> {
        let mut response = self.send_request(
            Method::POST,
            format!("{}/files", self.url),
            FilePostRequest {
                file_name: file_name.to_string(),
                beam_id,
            },
        )?;
        let file_params: FilePostResponse = response.json()?;
        Ok((
            file_params.file_id,
            file_params.storage_name,
            file_params.should_beam,
        ))
    }

    pub fn file_beam_end(
        &mut self,
        file_id: &str,
        err: Option<&str>,
        file_size: Option<usize>,
        file_checksum: Option<String>,
        mtime: Option<Mtime>,
    ) -> ScottyResult<()> {
        let error_string = match err {
            Some(err) => err,
            _ => "",
        };
        self.send_request(
            Method::PUT,
            format!("{}/files/{}", self.url, file_id),
            FileUpdateRequest {
                success: err.is_none(),
                error: error_string.to_string(),
                size: file_size,
                checksum: file_checksum,
                mtime,
            },
        )?;
        Ok(())
    }

    pub fn complete_beam(&mut self, beam_id: BeamId, error: Option<&str>) -> ScottyResult<()> {
        self.send_request(
            Method::PUT,
            format!("{}/beams/{}", self.url, beam_id),
            BeamUpdateRequest::new(true, error),
        )?;
        Ok(())
    }
}
