# EchoClientProtocol from asyncio Protocol examples
# Adapted to fit project specs

import asyncio
import sys

import config

class EchoClientProtocol(asyncio.Protocol):
    def __init__(self, message, loop):
        self.message = message
        self.loop = loop

    def connection_made(self, transport):
        for msg in self.message:
            transport.write(msg.encode())
        print('Data sent: {!r}'.format(self.message))

    def data_received(self, data):
        print('Data received: {}'.format(data.decode()))

    def connection_lost(self, exc):
        print('The server closed the connection')
        print('Stop the event loop')
        self.loop.stop()

if __name__ == '__main__':
    # Check usage
    if (len(sys.argv) != 2):
        # Sample Usage: cat command.txt | python3 client.py Goloman
        print('Error: Incorrect Usage.\nUsage: cat/echo [file/message] | python3 client.py [server-name]')
        exit(1)

    server_name = sys.argv[1]

    # Check valid server name
    if server_name not in config.SERVER_NAMES:
        print('Error: Invalid Server Name.\nValid names: Goloman, Hands, Holiday, Welsh, and Wilkes.')
        exit(1)

    port_number = config.SERVER_PORTS[server_name]
    message = sys.stdin.readlines()

    loop = asyncio.get_event_loop()
    coro = loop.create_connection(lambda: EchoClientProtocol(message, loop),
                                  config.LOCALHOST, port_number)
    loop.run_until_complete(coro)
    loop.run_forever()
    loop.close()
