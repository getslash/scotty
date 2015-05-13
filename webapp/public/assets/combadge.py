#!/usr/bin/env python
from __future__ import print_function
from contextlib import closing
import gzip
import logging
import os
import sys
import socket
import struct

logger = logging.getLogger("combadge")
_CHUNK_SIZE = 10 * 1024 * 1024


class ClientMessages(object):
    BeamComplete = 0
    StartBeamingFile = 1
    FileChunk = 2
    FileDone = 3


class ServerMessages:
    SkipFile = 0
    BeamFile = 1
    FileBeamed = 2


def chunk_iterator(f, chunk_size):
    while True:
        data = f.read(chunk_size)
        if not data:
            return

        yield data


class FileWriter(object):
    def __init__(self, transporter):
        self._transporter = transporter

    def write(self, data):
        self._transporter.sendall(struct.pack('!BL', ClientMessages.FileChunk, len(data)))
        self._transporter.sendall(data)

    def close(self):
        pass


def _beam_file(transporter, base_path, path):
    file_size = os.stat(path).st_size
    logger.info("Uploading {0} ({1} bytes)".format(path, file_size))

    transporter.sendall(struct.pack('!B', ClientMessages.StartBeamingFile))

    should_compress = os.path.splitext(path)[1] == ".log"
    store_path = path.replace(base_path, ".")
    if should_compress:
        store_path += ".gz"
    transporter.sendall(struct.pack('!H{0}s'.format(len(store_path)), len(store_path), store_path.encode('UTF-8')))
    logger.info("Compressing {0}".format(path))

    answer = struct.unpack('!B', transporter.recv(1))[0]
    if answer == ServerMessages.SkipFile:
        logger.info("Server asks us to skip this file")
        return
    elif answer == ServerMessages.BeamFile:
        logger.info("Server asks us to beam this file")
    else:
        raise Exception("Unexpected server response: {0}".format(answer))

    with open(path, 'rb') as f:
        file_writer = FileWriter(transporter)
        if should_compress:
            file_writer = gzip.GzipFile(mode="wb", fileobj=file_writer)
        with closing(file_writer):
            for chunk in chunk_iterator(f, _CHUNK_SIZE):
                file_writer.write(chunk)

    transporter.sendall(struct.pack('!B', ClientMessages.FileDone))
    answer = struct.unpack('!B', transporter.recv(1))[0]
    if answer == ServerMessages.FileBeamed:
        logger.info("Server reports that the file was beamed")
        return
    else:
        raise Exception("Unexpected server response: {0}".format(answer))


def beam_up(beam_id, path, transporter_addr):
    logger.info("Contacting transporter %s", transporter_addr)
    transporter = socket.socket()
    transporter.connect((transporter_addr, 9000))

    beam_id = int(beam_id)
    transporter.sendall(struct.pack('!Q', beam_id))

    if os.path.isfile(path):
        _beam_file(transporter, os.path.dirname(path), path)
    elif os.path.isdir(path):
        for (dirpath, _, filenames) in os.walk(path):
            for filename in filenames:
                rel_path = os.path.join(dirpath, filename)
                _beam_file(transporter, path, rel_path)

    transporter.sendall(struct.pack('!B', ClientMessages.BeamComplete))
    transporter.close()


def main():
    try:
        _, beam_id, path, transporter_addr = sys.argv
    except ValueError:
        print("Usage: combadge [beam id] [path] [transporter hostname]")
        return 1

    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    beam_up(beam_id, path, transporter_addr)


if __name__ == '__main__':
    sys.exit(main())
