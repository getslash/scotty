extern crate sentry;

use std::net::TcpListener;
use std::thread;
use std::io::Result;
use sentry::protocol::{Event, Map};
use super::beam::beam_up;
use super::storage::FileStorage;
use super::scotty::Scotty;

pub fn listen(storage: FileStorage, bind_address: &str, scotty_url: &str) -> Result<()> {
    let listener = match TcpListener::bind(&bind_address) {
        Ok(l) => l,
        Err(why) => panic!("Server bind error: {}", why),
    };

    debug!("Debug messages are on");
    info!("Listening for connections in {}", &bind_address);
    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                let storage = storage.clone();
                let mut tags = vec![];
                let scotty_url = String::from(scotty_url);

                match stream.peer_addr() {
                    Err(why) => error!("Cannot get peer address for socket: {}", why),
                    Ok(peer) => tags.push((format!("peer"), format!("{}", peer))),
                };
                thread::spawn(move || {
                    match beam_up(stream, storage, Scotty::new(scotty_url), &mut tags) {
                        Err(why) => {
                            if !why.is_disconnection() {
                                let event = {
                                    let mut event = Event::new();
                                    event.level = sentry::Level::Error;
                                    event.message = Some(format!("{}", why));

                                    let mut tag_map = Map::new();
                                    for tag in tags {
                                        let (key, value) = tag;
                                        tag_map.insert(key, value);
                                    }

                                    event.tags = tag_map;
                                    event
                                };

                                sentry::capture_event(event);
                            }

                            error!("Connection closed: {}", why);
                        }
                        Ok(_) => (),
                    };
                });
            }
            _ => (),
        }
    }

    drop(listener);
    Ok(())
}
