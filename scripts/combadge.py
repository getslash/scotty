#!/usr/bin/env python
from __future__ import print_function
import logging
import os
import sys
import socket
import struct

logger = logging.getLogger("combadge")


class ClientMessages(object):
    BeamComplete = 0
    StartBeamingFile = 1


class ServerMessages:
    SkipFile = 0
    BeamFile = 1
    FileBeamed = 2


def _beam_file(transporter, path):
    file_size = os.stat(path).st_size
    logger.info("Uploading {0} ({1} bytes)".format(path, file_size))

    transporter.sendall(struct.pack('!BQ', ClientMessages.StartBeamingFile, file_size))
    transporter.sendall(struct.pack('!H{0}s'.format(len(path)), len(path), path.encode('UTF-8')))

    answer = struct.unpack('!B', transporter.recv(1))[0]
    if answer == ServerMessages.SkipFile:
        logger.info("Server asks us to skip this file")
        return
    elif answer == ServerMessages.BeamFile:
        logger.info("Server asks us to beam this file")
    else:
        raise Exception("Unexpected server response: {0}".format(answer))

    with open(path, 'rb') as f:
        while True:
            chunk = f.read(2 ** 12)
            if not chunk:
                break
            transporter.sendall(chunk)

    answer = struct.unpack('!B', transporter.recv(1))[0]
    if answer == ServerMessages.FileBeamed:
        logger.info("Server reports that the file was beamed")
        return
    elif answer == ServerMessages.BeamFile:
        logger.info("Server asks us to beam this file")
    else:
        raise Exception("Unexpected server response: {0}".format(answer))


def beam_up(beam_id, path, transporter_addr):
    transporter = socket.socket()
    transporter.connect((transporter_addr, 9000))

    beam_id = int(beam_id)
    transporter.sendall(struct.pack('!Q', beam_id))

    if os.path.isfile(path):
        _beam_file(transporter, path)
    elif os.path.isdir(path):
        os.chdir(path)
        for (dirpath, _, filenames) in os.walk('.'):
            for filename in filenames:
                rel_path = os.path.join(dirpath, filename)
                _beam_file(transporter, rel_path)

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
