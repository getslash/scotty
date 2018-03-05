#!/usr/bin/env python
from __future__ import print_function
from contextlib import closing
import gzip
import logging
import os
import sys
import socket
import struct
import traceback
from time import sleep

logger = logging.getLogger("combadge")
_CHUNK_SIZE = 10 * 1024 * 1024
_SLEEP_TIME = 10
_NUM_OF_RETRIES = (60 // _SLEEP_TIME) * 15


class ClientMessages(object):
    BeamComplete = 0
    StartBeamingFile = 1
    FileChunk = 2
    FileDone = 3
    ProtocolVersion = 4


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

    should_compress = os.path.splitext(path)[1] not in ['.gz', '.bz2', '.xz', '.zst', '.tgz', '.tbz2', '.txz',
                                                        '.ioym', '.br']
    store_path = path.replace(base_path, ".", 1) if base_path else path
    if should_compress:
        store_path += ".gz"
        logger.info("Compressing {0}".format(path))
    transporter.sendall(struct.pack('!H{0}s'.format(len(store_path)), len(store_path), store_path.encode('UTF-8')))

    answer = struct.unpack('!B', transporter.recv(1))[0]
    if answer == ServerMessages.SkipFile:
        logger.info("Server asks us to skip this file")
        return
    elif answer == ServerMessages.BeamFile:
        logger.info("Server asks us to beam this file")
    else:
        raise Exception("Unexpected server response: {0}".format(answer))

    stat = os.stat(path)
    transporter.sendall(struct.pack('!Q', int(stat.st_mtime)))

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


def _beam_up(beam_id, path, transporter_addr):
    logger.info("Contacting transporter %s", transporter_addr)
    with closing(socket.socket()) as transporter:
        transporter.connect((transporter_addr, 9000))

        beam_id = int(beam_id)
        transporter.sendall(struct.pack('!Q', beam_id))

        transporter.sendall(struct.pack('!BH', ClientMessages.ProtocolVersion, 2))

        if os.path.isfile(path):
            _beam_file(transporter, os.path.dirname(path), path)
        elif os.path.isdir(path):
            logger.info("Entering {0}".format(path))
            for (dirpath, _, filenames) in os.walk(path):
                for filename in filenames:
                    rel_path = os.path.join(dirpath, filename)
                    if os.path.isfile(rel_path):
                        _beam_file(transporter, path, rel_path)
                    else:
                        logger.info("Skipping non-file {0}".format(rel_path))

        transporter.sendall(struct.pack('!B', ClientMessages.BeamComplete))


def beam_up(beam_id, path, transporter_addr):
    attempt = 1
    while True:
        try:
            _beam_up(beam_id, path, transporter_addr)
        except Exception:
            should_retry = attempt < _NUM_OF_RETRIES
            logger.error(
                "Attempt %d of beaming failed. %s. %s",
                attempt,
                "retrying" if should_retry else "exiting",
                traceback.format_exc())
            if not should_retry:
                raise
            else:
                logger.info("Sleeping %d seconds before reattempting (%d/%d)", _SLEEP_TIME, attempt, _NUM_OF_RETRIES)
                attempt += 1
                sleep(_SLEEP_TIME)
        else:
            break


def main():
    try:
        _, beam_id, path, transporter_addr = sys.argv
    except ValueError:
        print("Usage: combadge [beam id] [path] [transporter hostname]")
        return 1

    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    # decouple from parent environment
    os.setsid()
    os.umask(0)

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    with open("/dev/null", "w") as f:
        os.dup2(f.fileno(), sys.stdin.fileno())
        os.dup2(f.fileno(), sys.stdout.fileno())
        os.dup2(f.fileno(), sys.stderr.fileno())

    from logging.handlers import SysLogHandler
    handler = SysLogHandler('/dev/log')
    logger.setLevel("DEBUG")
    handler.setLevel("DEBUG")
    handler.setFormatter(logging.Formatter('combadge [beam {0}]: %(message)s'.format(beam_id)))
    logger.addHandler(handler)
    logger.info("Combadge forked")

    beam_up(beam_id, path, transporter_addr)


if __name__ == '__main__':
    try:
        sys.exit(main())
    finally:
        try:
            os.unlink(__file__)
        except OSError:
            pass
