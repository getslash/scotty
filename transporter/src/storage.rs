use super::error::{TransporterError, TransporterResult};
use std::fs::{metadata, File};
use std::io::Result;
use std::path::{Path, PathBuf};

#[derive(Clone)]
pub struct FileStorage {
    base_directory: String,
}

impl FileStorage {
    pub fn open(base_directory: &str) -> Result<FileStorage> {
        let path = Path::new(base_directory);
        metadata(&path)?;
        Ok(FileStorage {
            base_directory: String::from(base_directory),
        })
    }

    pub fn create(&self, file_name: &str) -> TransporterResult<File> {
        let mut path_buffer = PathBuf::new();
        path_buffer.push(&self.base_directory);
        path_buffer.push(file_name);
        let file = File::create(&path_buffer).map_err(TransporterError::StorageIoError)?;
        Ok(file)
    }
}
