# Author: Ryan O'Callaghan @ University of Western Ontario
# Date: 11/08/2022
# Version: 3.0 (FINAL)

"""
File to represent the client for a client-server game.

...

The client in this case represents a single player on the server, and will store all the player information, such as
what items they are holding, etc.
"""
import signal
from socket import *
import argparse
from typing import List
from urllib.parse import urlparse
import select
import sys

import select

OPERATION_SUCCESS = "operation_success"
OPERATION_FAILURE = "operation_failure"
OPERATION_JOIN = "server_join_success"

DISCOVERY_SERVER_PORT = 8888
DISCOVERY_FAIL = "NOTOK"
DISCOVERY_SUCCESS = "OK"

class Player:
    """
    A class to represent a Player of the game.

    ...

    Attributes
    ----------
    name : str
        Name of the player
    inventory : List[str]
        List of items the player is holding

    Methods
    -------
    remove_item(item_name: str)
        Remove's an item from player inventory, will be used in conjunction with the 'drop' command to drop an item
        into the server room.
    add_item(item_name: str)
        Add an item into player's inventory, used in conjunction with 'take' command to take an item from server room.
    display_inventory()
        Displays the contents of player inventory. If it is empty, report accordingly.
    """

    def __init__(self, name: str):
        self.name = name
        self.inventory = []

    def remove_item(self, item_name: str) -> bool:
        try:
            self.inventory.remove(item_name)
            return True
        except ValueError:
            return False

    def add_item(self, item_name: str) -> None:
        self.inventory.append(item_name)

    def display_inventory(self) -> None:
        print("You are holding:")

        if not self.inventory:
            print("\tInventory is empty.")
            return

        for item in self.inventory:
            print("\t", item)


def disconnect_player(signum, frame) -> None:
    print()
    print("Disconnecting", player.name, "...")
    # Let server know we are exiting.
    exit_code = "exit," + player.name
    client_socket.sendto(exit_code.encode(), (server_address.hostname, server_address.port))

    # Send a command to drop all items in player inventory as player is leaving room.
    for player_item in player.inventory:
        command = "drop " + player_item
        client_socket.sendto(command.encode(), (server_address.hostname, server_address.port))

    # Finally, close the client socket.
    client_socket.close()
    exit(0)


def process_command():
    global server_address
    global server_hostname
    global server_port
    global player

    client_input = input()

    if client_input.find("say") != -1:
        try:
            check_validity = client_input.split()

            check_validity[1]

            check_validity.pop(0)

            print("You said \"" + " ".join(check_validity) + "\".")
            client_socket.sendto(client_input.encode(), (server_address.hostname, server_address.port))

        except IndexError:
            print("What did you want to say?")

    elif client_input == "look":
        # Ask the server for current room contents.
        client_socket.sendto(client_input.encode(), (server_address.hostname, server_address.port))
        message_back, from_server_addr = client_socket.recvfrom(2048)
        print(message_back.decode())

    elif client_input == "inventory":
        player.display_inventory()

    elif client_input.find("take") != -1:
        # Ask the server to see if it exists, then remove from inventory.
        client_socket.sendto(client_input.encode(), (server_address.hostname, server_address.port))

        pair_input = client_input.split(' ')

        # Returns either successful_remove, or error_remove
        message_back, from_server_addr = client_socket.recvfrom(2048)

        if message_back.decode() == OPERATION_SUCCESS:
            # Add item to player inventory.

            # Note: if OPERATION_SUCCESS, then we do not have to worry about going out of bounds because the
            #       command was validated by the server.
            item = pair_input[1]

            player.add_item(str(item))
            print(item, "taken.")
        else:
            print("Error: item not in room.")

    elif client_input.find("drop") != -1:
        # Check if it exists in inventory, then ask server to add.
        pair_input = client_input.split(' ')
        try:
            item = pair_input[1]

            if player.remove_item(str(item)):
                # Tell server to add item.
                client_socket.sendto(client_input.encode(), (server_address.hostname, server_address.port))
                print(item, "dropped.")
            else:
                print("You are not holding", item)
        except IndexError:
            print("Invalid command:", client_input)

    elif client_input == "exit":

        # Using the same signal exit handler to exit when given the command.
        disconnect_player(0, 0)

    elif client_input == "north":
        # Check if a room north exists, if not send error msg.
        # If it does exist, let the server know you are leaving there.
        # Change the server_address and port on client to new information.
        # Send look command to server to see new contents.
        client_socket.sendto(client_input.encode(), (server_address.hostname, server_address.port))

        message_back, from_server_addr = client_socket.recvfrom(2048)

        if message_back.decode() == OPERATION_FAILURE:
            print("There is no room to the north.")
        else:
            # Room exists
            # Server will send new address back.
            server_address = urlparse(message_back.decode())
            server_hostname = server_address.hostname
            server_port = server_address.port

            join_message = "new_connection," + player.name
            client_socket.sendto(join_message.encode(), (server_hostname, server_port))

            client_socket.sendto("look".encode(), (server_hostname, server_port))
            message_back, from_server_addr = client_socket.recvfrom(2048)
            print(message_back.decode())

    elif client_input == "east":

        client_socket.sendto(client_input.encode(), (server_address.hostname, server_address.port))

        message_back, from_server_addr = client_socket.recvfrom(2048)

        if message_back.decode() == OPERATION_FAILURE:
            print("There is no room to the east.")
        else:
            server_address = urlparse(message_back.decode())
            server_hostname = server_address.hostname
            server_port = server_address.port

            join_message = "new_connection," + player.name
            client_socket.sendto(join_message.encode(), (server_hostname, server_port))

            client_socket.sendto("look".encode(), (server_hostname, server_port))
            message_back, from_server_addr = client_socket.recvfrom(2048)
            print(message_back.decode())

    elif client_input == "south":

        client_socket.sendto(client_input.encode(), (server_address.hostname, server_address.port))

        message_back, from_server_addr = client_socket.recvfrom(2048)

        if message_back.decode() == OPERATION_FAILURE:
            print("There is no room to the south.")
        else:
            server_address = urlparse(message_back.decode())
            server_hostname = server_address.hostname
            server_port = server_address.port

            join_message = "new_connection," + player.name
            client_socket.sendto(join_message.encode(), (server_hostname, server_port))

            client_socket.sendto("look".encode(), (server_hostname, server_port))
            message_back, from_server_addr = client_socket.recvfrom(2048)
            print(message_back.decode())

    elif client_input == "west":

        client_socket.sendto(client_input.encode(), (server_address.hostname, server_address.port))

        message_back, from_server_addr = client_socket.recvfrom(2048)

        if message_back.decode() == OPERATION_FAILURE:
            print("There is no room to the west.")
        else:
            server_address = urlparse(message_back.decode())
            server_hostname = server_address.hostname
            server_port = server_address.port

            join_message = "new_connection," + player.name
            client_socket.sendto(join_message.encode(), (server_hostname, server_port))

            client_socket.sendto("look".encode(), (server_hostname, server_port))
            message_back, from_server_addr = client_socket.recvfrom(2048)
            print(message_back.decode())

    elif client_input == "up":

        client_socket.sendto(client_input.encode(), (server_address.hostname, server_address.port))

        message_back, from_server_addr = client_socket.recvfrom(2048)

        if message_back.decode() == OPERATION_FAILURE:
            print("There is no room above.")
        else:
            server_address = urlparse(message_back.decode())
            server_hostname = server_address.hostname
            server_port = server_address.port

            join_message = "new_connection," + player.name
            client_socket.sendto(join_message.encode(), (server_hostname, server_port))

            client_socket.sendto("look".encode(), (server_hostname, server_port))
            message_back, from_server_addr = client_socket.recvfrom(2048)
            print(message_back.decode())

    elif client_input == "down":

        client_socket.sendto(client_input.encode(), (server_address.hostname, server_address.port))

        message_back, from_server_addr = client_socket.recvfrom(2048)

        if message_back.decode() == OPERATION_FAILURE:
            print("There is no room below.")
        else:
            server_address = urlparse(message_back.decode())
            server_hostname = server_address.hostname
            server_port = server_address.port

            join_message = "new_connection," + player.name
            client_socket.sendto(join_message.encode(), (server_hostname, server_port))

            client_socket.sendto("look".encode(), (server_hostname, server_port))
            message_back, from_server_addr = client_socket.recvfrom(2048)
            print(message_back.decode())

    else:
        print("Invalid command: ", client_input)


def process_server_msg():
    # print("The server sent a message!\n")
    message, client_address = client_socket.recvfrom(2048)

    if message.decode() == "exit":
        print("Server shutting down... Disconnecting...\n")
        disconnect_player(0, 0)

    print(message.decode())


def main():
    global player
    global client_socket
    global client_input
    global server_address
    global server_hostname
    global server_port

    # Create parser to take in arguments "player_name" and "server_address" to create new player and connect them to the
    # respective server.
    parser = argparse.ArgumentParser(description="Create a new player client")
    parser.add_argument("player_name", type=str, help="Name of player")
    parser.add_argument("server_name", type=str, help="Name of server you wish to connect to")

    args = parser.parse_args()

    # Parse the given server address for ease of use.
    # server_address = urlparse(args.server_address)
    # server_hostname = server_address.hostname
    # server_port = server_address.port

    # Create player object for client. List of items is empty initially.
    player = Player(args.player_name)

    # Testing
    # print("Player name:", args.player_name, "\nServer Address:", args.server_address)
    # print("hostname:", server_hostname)
    # print("port:", server_port)

    client_socket = socket(AF_INET, SOCK_DGRAM)

    # Get server address from DISCOVERY SERVER
    lookup_msg = f'LOOKUP {args.server_name}'
    client_socket.sendto(lookup_msg.encode(), ("", DISCOVERY_SERVER_PORT))
    message_back, _ = client_socket.recvfrom(2048)

    if message_back.decode() == DISCOVERY_FAIL:
        print("Error: Unable to receive address from discovery server.")
        disconnect_player(0, 0)
    else:
        server_address = urlparse(message_back.decode())
        server_hostname = server_address.hostname
        server_port = server_address.port

        print(f'CONNECTION SUCCESS: {server_hostname}, {server_port}')

    # Create signal object to catch CTRL+C for exit.
    signal.signal(signal.SIGINT, disconnect_player)

    # Send a join message to the server letting it know we are joining and wish to continue passing messages until exit.
    join_message = "new_connection," + args.player_name
    client_socket.sendto(join_message.encode(), (server_hostname, server_port))

    # Get initial room contents from server.
    client_socket.sendto("look".encode(), (server_hostname, server_port))
    message_back, from_server_addr = client_socket.recvfrom(2048)
    print(message_back.decode())

    client_input = ""
    while client_input != "exit":

        readers, _, _ = select.select([sys.stdin, client_socket], [], [])

        for reader in readers:
            if reader is client_socket:
                client_socket.settimeout(5)
                process_server_msg()
            else:
                process_command()


if __name__ == "__main__":
    main()