# EchoServerClientProtocol from asyncio Protocol examples
# Adapted to fit project specs

import aiohttp
import asyncio
import datetime
import json
import logging
import sys
import time

import config

# Added exception handler to gracefully log errors when they occur
def exception_handler(loop, context):
    try:
        exception = context['exception']
        # Handles exception where neighboring server is not up so we can't propagate data to it
        if isinstance(exception, ConnectionRefusedError):
            logger.error('Error: Could not connect to neighboring server, it is down/not up yet')
        else:
            logger.error('Error: {}'.format(context['exception']))
    except KeyError:
        logger.error('Error: {}'.format(context['message']))

# ClientServerProtocol class handles the propagating of client location messages
# Used by ServerClient class to act as a client and connect to neighboring servers
class ClientServerProtocol(asyncio.Protocol):
    def __init__(self, message):
        self.message = message

    def connection_made(self, transport):
        self.transport = transport
        logger.info('Sending updated location for {}'.format(self.message.split()[3]))
        self.transport.write(self.message.encode())

    # Neighboring server will send confirmation message once it successfully updates the client's location
    def data_received(self, data):
        message = data.decode()
        logger.info('{}'.format(message))
        logger.info('Closing connection to server {}'.format(message.split()[0]))
        self.transport.close()

    def connection_lost(self, exc):
        self.transport.close()

# ServerClient class handles the overall server state
# Updates dictionary of clients whose locations it is aware of and propagates info to neighboring servers
# Sends HTTP request to the Google Places API and processes the response
class ServerClient:

    # ServerClientProtocol class handles each individual connection
    # Determines how messages are interpreted and how to respond to each type of message
    # Sends proper response to each individual connected client
    class ServerClientProtocol(asyncio.Protocol):
        def __init__(self, server):
            self.server = server
            self.buffer = ''

        def connection_made(self, transport):
            self.peername = transport.get_extra_info('peername')
            logger.info('New incoming connection from {}'.format(self.peername))
            self.transport = transport

        # Uses buffer since data_received callback doesn't guarantee to get data terminated by a newline
        def data_received(self, data):
            data = data.decode()
            self.buffer += data
            self.handle_lines()

        def connection_lost(self, exc):
            logger.info('Client {} dropped connection'.format(self.peername))

        # Handles multiple lines in a single message one line at a time
        def handle_lines(self):
            while '\n' in self.buffer:
                try:
                    message, self.buffer = self.buffer.split('\n', 1)
                except ValueError:
                    response = '? {}\n'.format(self.buffer)
                    self.transport.write(response.encode())
                    self.buffer = ''

                logger.info('Message received: {!r}'.format(message))
                message_list = message.split()

                if not self.valid_message(message_list):
                    logger.error('Error: Received invalid message')
                    response = '? {}\n'.format(message)

                    logger.info('Sending response: {!r}'.format(response))
                    self.transport.write(response.encode())
                else:
                    self.handle_message(message_list)

        def handle_message(self, message):
            if message[0] == 'IAMAT':
                self.process_IAMAT_message(message[1], message[2], message[3])
            elif message[0] == 'WHATSAT':
                self.process_WHATSAT_message(message[1], message[2], message[3])
            elif message[0] == 'AT':
                self.process_AT_message(message)

        # Parses string containing the latitude and longitude, returns them as strings
        def parse_coords(self, coords):
            latitude, longitude = '', ''
            found_first, found_second = False, False

            for char in coords:
                if found_first and (char == '+' or char == '-'):
                    found_second = True

                if found_second:
                    longitude += char
                else:
                    latitude += char

                if not found_first:
                    found_first = True

            return latitude, longitude

        # Checks to make sure that the latitude and longitude coordinates provided are valid
        def valid_coords(self, coords):
            latitude, longitude = self.parse_coords(coords)

            try:
                latitude, longitude = float(latitude), float(longitude)
            except ValueError:
                return False

            if latitude > 90 or latitude < -90: return False
            if longitude > 180 or longitude < -180: return False

            return True

        # Checks to make sure that the received message is valid
        def valid_message(self, message):
            try:
                cmd = message[0]
                args = message[1:]
            except IndexError:
                return False

            if cmd == 'IAMAT':
                if len(args) != 3:
                    logger.error('Error: invalid number of IAMAT message arguments => {}'.format(args))
                    return False
                if not self.valid_coords(args[1]):
                    logger.error('Error: invalid latitude/longitude for IAMAT message')
                    return False
                try:
                    timestamp = float(args[2])
                    datetime.datetime.utcfromtimestamp(timestamp)
                except ValueError:
                    logger.error('Error: invalid timestamp for IAMAT message')
                    return False
                return True
            elif cmd == 'WHATSAT':
                if len(args) != 3:
                    logger.error('Error: invalid number of WHATSAT query arguments => {}'.format(args))
                    return False
                try:
                    client = self.server.clients[args[0]]
                except KeyError:
                    logger.error('Error: invalid client for WHATSAT query, server does not have its location yet')
                    return False
                try:
                    radius = float(args[1])
                    bound = int(args[2])
                except ValueError:
                    logger.error('Error: invalid types for radius and bound in WHATSAT query')
                    return False
                if radius > 50 or radius < 0:
                    logger.error('Error: radius is out of range for WHATSAT query')
                    return False
                if bound > 20 or bound < 0:
                    logger.error('Error: bound is out of range for WHATSAT query')
                    return False
                return True
            elif cmd == 'AT':
                return True
            else:
                return False

        def process_IAMAT_message(self, client_id, coords, timestamp):
            time_diff = float(time.time()) - float(timestamp)
            time_diff_str = '{}'.format(time_diff)
            if time_diff > 0:
                time_diff_str = '+' + time_diff_str

            client_stamp = 'AT {} {} {} {} {}'.format(self.server.server_name, time_diff_str, client_id, coords, timestamp)

            # Tries to update client's location and propagates updated location to neighboring servers if successful
            if self.server.update_clients(client_id, client_stamp):
                # Add own server name to end of message so that we can keep track of which servers have already received the updated location
                self.server.flood_update('{} {}\n'.format(client_stamp, self.server.server_name))
            else:
                logger.info('Did not propagate client stamp')

            response = '{}\n'.format(self.server.clients[client_id])
            logger.info('Sending response: {!r}'.format(response))
            self.transport.write(response.encode())

        def process_WHATSAT_message(self, client_id, radius, bound):
            # Grab most recent stamp for client which includes its most recent location, the most recent server it talked to, and the time at which they talked
            client_stamp = self.server.clients[client_id]

            # Construct the parameters necessary to make the request to the Google Places API
            client_info = client_stamp.split()
            radius = str(float(radius) * 1000)
            bound = int(bound)
            latitude, longitude = self.parse_coords(client_info[4])
            latitude = latitude.replace('+', '')
            longitude = longitude.replace('+', '')
            params = {'location': '{},{}'.format(latitude, longitude), 'radius': radius, 'key': config.API_KEY}

            loop = asyncio.get_event_loop()
            # Create task to run asynchronously which sends the HTTP request to the Google Places API
            task = loop.create_task(self.server.send_request(client_stamp, bound, params))
            # Add callback for when the task is done to retrieve the response
            task.add_done_callback(self.get_response)

        # Callback which is called when the HTTP request completes and the response message is constructed
        def get_response(self, task):
            response = task.result()
            logger.info('Sending response: {}'.format(response))
            self.transport.write(response.encode())

        def process_AT_message(self, message):
            # Identify which client is being updated and which server is sending the updated information
            client_id = message[3]
            source = message[-1]
            logger.info('Incoming AT message from {} is server {} propagating updated client location for {}'.format(self.peername, source, client_id))

            # Grab only the necessary info for the client stamp so the server can update its location
            client_stamp = ' '.join(message[:6])
            self.server.update_clients(client_id, client_stamp)

            message_str = ' '.join(message)
            # Add own server name to end of message so that we can keep track of which servers have already received the updated location
            self.server.flood_update('{} {}\n'.format(message_str, self.server.server_name))

            # Send confirmation message that client's location was updated so that the server sending the updated information can close its endpoint
            response = '{} received updated location for {}'.format(self.server.server_name, client_id)
            self.transport.write(response.encode())

    def __init__(self, server_name, port_number, loop):
        self.server_name = server_name
        self.clients = {}
        self.floodlist = config.FLOODLIST[server_name]
        self.server = loop.create_server(lambda: self.ServerClientProtocol(self), config.LOCALHOST, port_number)

    def update_clients(self, client_id, client_stamp):
        if client_id != client_stamp.split()[3]:
            logger.error('Error: incorrect call to update_clients.')
            return False

        success = False

        try:
            new_timestamp = float(client_stamp.split()[5])
            old_timestamp = float(self.clients[client_id].split()[5])

            # Only update client's location if the new timestamp is more recent than the old timestamp
            if new_timestamp > old_timestamp:
                self.clients[client_id] = client_stamp
                success = True
        except KeyError:
            # We don't have the client's location yet, add it to our dictionary
            self.clients[client_id] = client_stamp
            success = True

        if success:
            logger.info('Succesfully updated client stamp for {}'.format(client_id))
        else:
            logger.info('Did not update client stamp for {}'.format(client_id))

        return success

    def flood_update(self, message):
        # Grab list of servers that already received the updated location to prevent the message from propagating from server to server forever
        # These servers added their own name to the end of the AT message for this purpose
        logger.info('Propagating updated client stamp for {}'.format(message.split()[3]))
        received_update_list = message.split()[6:]
        logger.info('Received update list: {}'.format(received_update_list))
        for server_name in self.floodlist:
            # Only propagate updated location to servers that have not yet received the message
            if server_name not in received_update_list:
                loop = asyncio.get_event_loop()
                logger.info('Connecting to server {}'.format(server_name))
                coro = loop.create_connection(lambda: ClientServerProtocol(message), config.LOCALHOST, config.SERVER_PORTS[server_name])
                # Create task to run asynchronously which sends the updated location to the neighboring server
                loop.create_task(coro)

    # Asynchronous coroutine to handle sending the HTTP request to the Google Places API and processing the response
    @asyncio.coroutine
    async def send_request(self, client_stamp, bound, params):
        async with aiohttp.ClientSession() as session:
            async with session.get(config.API_URL, params=params) as response:
                json_result = await response.json()
                # Limit number of results as specified by the bound argument in the WHATSAT query
                if len(json_result['results']) > bound:
                    json_result['results'] = json_result['results'][:bound]
                json_dump = json.dumps(json_result, indent=2)
        await session.close()

        # Constructs proper response containing the client's most recent stamp and the JSON response
        response = '{}\n{}\n\n'.format(client_stamp, json_dump)
        # Returns response to ServerClientProtocol via the task callback
        return response

if __name__ == '__main__':
    # Check usage
    if len(sys.argv) != 2:
        print('Error: Incorrect Usage.\nUsage: python3 server.py [server-name]')
        exit(1)

    server_name = sys.argv[1]

    # Check valid server name
    if server_name not in config.SERVER_NAMES:
        print('Error: Invalid Server Name.\nValid names: Goloman, Hands, Holiday, Welsh, and Wilkes.')
        exit(1)

    port_number = config.SERVER_PORTS[server_name]

    # Setup server logging
    log_format = '%(asctime)s - %(levelname)s (%(name)s) => %(message)s'
    formatter = logging.Formatter(log_format)

    logger = logging.getLogger(server_name)
    logger.setLevel(logging.INFO)

    log_path = config.LOG_PATHS[server_name]
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Startup server using asyncio
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(exception_handler)
    coro = ServerClient(server_name, port_number, loop)
    server = loop.run_until_complete(coro.server)

    logger.info('Created server: {}, serving on {}'.format(server_name, server.sockets[0].getsockname()))

    # Serve requests until Ctrl+C is pressed
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
