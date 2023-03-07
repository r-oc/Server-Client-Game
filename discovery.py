# Author: Ryan O'Callaghan @ University of Western Ontario
# Date: 12/08/2022
# Version: 3.0 (FINAL)

"""
File to represent the server for a server discovery system. It will represent
server addresses as names so a client can connect with the name of the sever
only, and this service will map to the address.

...

"""

from socket import *
import signal

# Operation constants.
OPERATION_SUCCESS = "OK"
OPERATION_FAILURE = "NOTOK"
LISTENING_PORT = 8888

# Variables for the discovery system.
server_map = {}  # Map "name"->address


def main():
    print("Welcome to the Server Discovery Registry")

    server_socket = socket(AF_INET, SOCK_DGRAM)

    server_socket.bind(('', LISTENING_PORT))
    print(f'Listening on port {LISTENING_PORT} ... ')

    def server_terminate(signum, frame):
        print()
        print("Interrupt received, shutting down discovery service...")
        exit(0)

    # Terminate if CTRL+C received.
    signal.signal(signal.SIGINT, server_terminate)

    while True:
        # print(f"Current list: {server_map}")  # Testing

        message, client_address = server_socket.recvfrom(2048)

        if message.decode().find("DEREGISTER") != -1:
            parsed_message = message.decode().split(' ')

            try:
                new_server_name = parsed_message[1]

                removed_server = server_map.pop(new_server_name)

                # Let the server know that the address was deregistered successfully.
                print(f'-Deregistered server: {removed_server}')
                server_socket.sendto(OPERATION_SUCCESS.encode(), client_address)

            except KeyError:
                # Name does not exist.
                server_socket.sendto(OPERATION_FAILURE.encode(), client_address)

            except IndexError:
                # Invalid formatting
                server_socket.sendto(OPERATION_FAILURE.encode(), client_address)

        elif message.decode().find("REGISTER") != -1:
            # TODO Check if given address is valid (Not a req.)
            parsed_message = message.decode().split(' ')

            try:
                new_address = parsed_message[1]
                new_server_name = parsed_message[2]

                # Add new entry:
                server_map[new_server_name] = new_address

                # Let the server know that the new address was registered successfully.
                print(f'+Registered {new_server_name} on address:{new_address}')
                server_socket.sendto(OPERATION_SUCCESS.encode(), client_address)

            except KeyError:
                # This is more likely to happen, duplicate key error.
                server_socket.sendto(OPERATION_FAILURE.encode(), client_address)

            except IndexError:
                # Error, not correct formatting.
                # Note that this would probably never trip, because the server is
                # sending that and not a user.
                server_socket.sendto(OPERATION_FAILURE.encode(), client_address)

        elif message.decode().find("LOOKUP") != -1:
            parsed_message = message.decode().split(' ')

            try:
                name_to_search = parsed_message[1]

                return_address = server_map[name_to_search]

                server_socket.sendto(return_address.encode(), client_address)

            except KeyError:
                # Not found, return failure.
                server_socket.sendto(OPERATION_FAILURE.encode(), client_address)

            except IndexError:
                # Invalid format.
                server_socket.sendto(OPERATION_FAILURE.encode(), client_address)


if __name__ == "__main__":
    main()