# Author: Ryan O'Callaghan @ University of Western Ontario
# Date: 11/08/2022
# Version: 3.0 (FINAL)

"""
File to represent the server for a client-server game.

...

The server in this case represents a single room in the game, it will contain items and allow a client (player) to join
and interact with the room.
"""

from socket import *
import argparse
from typing import List
import signal
from urllib.parse import urlparse

# Imported so the server can access player objects.
# from player import Player

OPERATION_SUCCESS = "operation_success"
OPERATION_FAILURE = "operation_failure"
OPERATION_JOIN = "server_join_success"

DISCOVERY_SERVER_PORT = 8888
DISCOVERY_FAIL = "NOTOK"
DISCOVERY_SUCCESS = "OK"


class Room:
    """
    A class to represent a Room in the game.

    ...

    Attributes
    ----------
    name : str
        Name of the room.
    desc : str
        A short description of how the room would look, behave, etc.
    items : List[str]
        List of items that are currently in the room.
    players : List[str]
        List of all the players currently in the room. By client ADDRESS

    Methods
    -------
    remove_item(item_name: str)
        Remove an item from the 'inventory' of the room.
    add_item(item_name: str)
        Add an item to the room.
    display_contents()
        Displays the contents of the room. If it is empty, report accordingly.
    """

    def __init__(self, name: str, desc: str, items: List[str], players: List[str]):
        self.name = name
        self.desc = desc
        self.items = items
        self.players = players

    def remove_item(self, item_name: str) -> bool:
        try:
            self.items.remove(item_name)
            return True
        except ValueError:
            return False

    def add_item(self, item_name: str) -> None:
        self.items.append(item_name)

    def get_player_name_by_port(self, parsed_port: int) -> str:

        for player in self.players:
            address = player.split(',')
            port_num = address[1].split('-')
            port_num[0] = port_num[0].strip('()').strip()

            if parsed_port == int(port_num[0]):
                return port_num[1]

        return "Player Not Found"

    def __str__(self):
        string = self.name + "\n\n" + self.desc + "\n\n"

        string = string + "In this room, there are:\n"

        if not self.items:
            string = string + "The room is empty.\n"
            return string

        for item in self.items:
            string = string + "\t" + str(item) + "\n"

        return string


def get_server_address(server_name: str) -> str:
    """

    Function to get the server address from the name provided. It will query the discovery
    server and ask for the mapped address.

    :param server_name: Name of the server you wish to receive the address from.
    :return: the specified address or NULL(None) because that will indicate that there is no server with that name.
    """
    if server_name is not None:

        message_out = f'LOOKUP {server_name}'

        server_socket.sendto(message_out.encode(), ("", DISCOVERY_SERVER_PORT))
        message_back, _ = server_socket.recvfrom(2048)

        if message_back.decode() == DISCOVERY_FAIL:
            # This failure is most likely because of a NOT found error, thus we return None.
            return None
        else:
            # Otherwise, we return the address.
            return message_back.decode()
    else: return None


def main():

    global server_socket

    parser = argparse.ArgumentParser(description="Create a new server room")
    # parser.add_argument("port", type=int, help="Server port")
    parser.add_argument("name", type=str, help="Name of room")
    parser.add_argument("description", type=str, help="Room description")
    parser.add_argument("items", nargs="+", help="List of items in room")
    parser.add_argument("-n", "--north", type=str, help="Name of server north of this one.")
    parser.add_argument("-e", "--east", type=str, help="Name of server east of this one.")
    parser.add_argument("-s", "--south", type=str, help="Name of server south of this one.")
    parser.add_argument("-w", "--west", type=str, help="Name of server west of this one.")
    parser.add_argument("-u", "--up", type=str, help="Name of server above (up) of this one.")
    parser.add_argument("-d", "--down", type=str, help="Name of server below (down) of this one.")

    args = parser.parse_args()

    room_name = args.name
    description = args.description
    items = args.items

    # Create room object for server.
    room = Room(room_name, description, items, [])

    print("Room Starting Description:")
    print(str(room))

    server_socket = socket(AF_INET, SOCK_DGRAM)
    server_socket.bind(('', 0))
    print("Room will wait for players at port:", server_socket.getsockname()[1])

    # The args.DIRECTION will now return the NAME of the requested server.
    north_room = get_server_address(args.north)
    east_room = get_server_address(args.east)
    south_room = get_server_address(args.south)
    west_room = get_server_address(args.west)
    up_room = get_server_address(args.up)
    down_room = get_server_address(args.down)

    def server_terminate(signum, frame):
        print()
        print("Interrupt received, shutting server down ...")

        dereg_msg = f'DEREGISTER {room_name}'
        server_socket.sendto(dereg_msg.encode(), ("", DISCOVERY_SERVER_PORT))
        message_back, _ = server_socket.recvfrom(2048)

        # Tell all clients shut down is in progress.
        for player in room.players:
            address = player.split(',')
            port_num = address[1].split('-')
            port_num[0] = port_num[0].strip('()')

            server_socket.sendto("exit".encode(), ("", int(port_num[0])))

        exit(0)

    # REGISTER SERVER BEFORE START LISTENING FOR COMMANDS
    reg_msg = f'REGISTER room://localhost:{server_socket.getsockname()[1]} {room_name}'
    server_socket.sendto(reg_msg.encode(), ("", DISCOVERY_SERVER_PORT))
    message, _ = server_socket.recvfrom(2048)
    if message.decode() == DISCOVERY_FAIL:
        print(f"Unable to register current server room: {reg_msg}")
        server_terminate(0, 0)
    else:
        print("Room successfully registered.")

    signal.signal(signal.SIGINT, server_terminate)

    while True:
        print(f'players: {room.players}')
        message, client_address = server_socket.recvfrom(2048)

        parsed_port = str(client_address)
        parsed_port = parsed_port.split(',')
        parsed_port = parsed_port[1].strip('()')
        parsed_port = parsed_port.strip()

        # Upon connection, client will send a specified message to the server indicating that they are connected, and
        # will also send a message upon disconnection.
        if message.decode().find("new_connection,") != -1:
            connection = message.decode().split(',')
            print("User", connection[1], "joined from address", client_address)

            # Append the new player to player list in this format:
            #                                   "name".(ip, port)
            # This is because there may be two players connecting with name "bob"
            new_player = str(client_address) + "-" + connection[1]
            room.players.append(new_player)

            # Send message to players
            for player in room.players:
                address = player.split(',')
                port_num = address[1].split('-')
                port_num[0] = port_num[0].strip('()')

                if int(parsed_port) != int(port_num[0]):
                    join_message = connection[1] + " entered the room."
                    server_socket.sendto(join_message.encode(), ("127.0.0.1", int(port_num[0])))

        elif message.decode().find("say") != -1:
            # send the message to everyone on the server.

            for player in room.players:
                address = player.split(',')
                port_num = address[1].split('-')
                port_num[0] = port_num[0].strip('()')

                if int(parsed_port) != int(port_num[0]):
                    i_msg = message.decode().split()
                    i_msg.pop(0)

                    name = room.get_player_name_by_port(int(parsed_port))

                    new_message = name + " said \""
                    new_message = new_message + " ".join(i_msg) + "\"."

                    server_socket.sendto(new_message.encode(), ("127.0.0.1", int(port_num[0])))


        elif message.decode() == "look":

            room_contents = str(room)

            # Now we should display the players.
            for player in room.players:
                player_name = player.split('-')

                # The player contains the ip,port and player name, however port is the only
                # unique identifier. Ex: Many players called "bob" can join from the same PC.
                if player.find(str(client_address)) == -1:
                    room_contents = room_contents + "\t" + str(player_name[1]) + "\n"

            # Now show the rooms adjacent.
            if north_room is not None:
                room_contents = room_contents + "A doorway leads away from the room to the north.\n"

            if south_room is not None:
                room_contents = room_contents + "A doorway leads away from the room to the south.\n"

            if east_room is not None:
                room_contents = room_contents + "A doorway leads away from the room to the east.\n"

            if west_room is not None:
                room_contents = room_contents + "A doorway leads away from the room to the west.\n"

            if up_room is not None:
                room_contents = room_contents + "A latch on the roof leads away from the room above.\n"

            if down_room is not None:
                room_contents = room_contents + "A latch on the ground leads away from the room below.\n"

            server_socket.sendto(room_contents.encode(), client_address)

        elif message.decode().find("take") != -1:
            # Check if item exists, if not report error, otherwise remove item.
            pair_input = message.decode().split(' ')

            # Attempt to remove item and let client know the status.
            try:
                item = pair_input[1]

                if room.remove_item(item):
                    # Removed successfully
                    server_socket.sendto(OPERATION_SUCCESS.encode(), client_address)
                else:
                    server_socket.sendto(OPERATION_FAILURE.encode(), client_address)

            # If there is no item in pair_input[1] the command entered is incorrect.
            # I.e. user could have entered takeitem or just take which is invalid.
            except IndexError:
                server_socket.sendto(OPERATION_FAILURE.encode(), client_address)

        elif message.decode().find("drop") != -1:
            pair_input = message.decode().split(' ')

            # This shouldn't cause an IndexError ever, because the client will only
            # send a drop command if it is valid. But someone not using my client
            # could break this so should check.
            item = pair_input[1]

            room.add_item(str(item))

        elif message.decode() == "north":
            if north_room is None:
                server_socket.sendto(OPERATION_FAILURE.encode(), client_address)
            else:

                # Tell the rest of the server that X-player left.
                for player in room.players:
                    address = player.split(',')
                    port_num = address[1].split('-')
                    port_num[0] = port_num[0].strip('()')

                    if int(parsed_port) != int(port_num[0]):
                        name = room.get_player_name_by_port(int(parsed_port))

                        new_message = name + " left the room, heading north.\n"

                        server_socket.sendto(new_message.encode(), ("127.0.0.1", int(port_num[0])))

                # Remove player from current server.
                try:
                    # Remove the player with the same format they were added to player list.
                    player_to_remove = str(client_address) + "-" + room.get_player_name_by_port(int(parsed_port))

                    room.players.remove(player_to_remove)
                    print("User moved north: ", str(client_address))
                except ValueError:
                    print("User does not exist.")

                server_socket.sendto(north_room.encode(), client_address)

        elif message.decode() == "east":
            if east_room is None:
                server_socket.sendto(OPERATION_FAILURE.encode(), client_address)
            else:

                for player in room.players:
                    address = player.split(',')
                    port_num = address[1].split('-')
                    port_num[0] = port_num[0].strip('()')

                    if int(parsed_port) != int(port_num[0]):
                        name = room.get_player_name_by_port(int(parsed_port))

                        new_message = name + " left the room, heading east.\n"

                        server_socket.sendto(new_message.encode(), ("127.0.0.1", int(port_num[0])))

                # Remove player from current server.
                try:

                    player_to_remove = str(client_address) + "-" + room.get_player_name_by_port(int(parsed_port))

                    room.players.remove(player_to_remove)
                    print("User moved east: ", str(client_address))
                except ValueError:
                    print("User does not exist.")

                server_socket.sendto(east_room.encode(), client_address)

        elif message.decode() == "south":
            if south_room is None:
                server_socket.sendto(OPERATION_FAILURE.encode(), client_address)
            else:

                # Tell the rest of the server that X-player left.
                for player in room.players:
                    address = player.split(',')
                    port_num = address[1].split('-')
                    port_num[0] = port_num[0].strip('()')

                    if int(parsed_port) != int(port_num[0]):
                        name = room.get_player_name_by_port(int(parsed_port))

                        new_message = name + " left the room, heading south.\n"

                        server_socket.sendto(new_message.encode(), ("127.0.0.1", int(port_num[0])))

                # Remove player from current server.
                try:
                    # Remove the player with the same format they were added to player list.
                    player_to_remove = str(client_address) + "-" + room.get_player_name_by_port(int(parsed_port))

                    room.players.remove(player_to_remove)
                    print("User moved south: ", str(client_address))
                except ValueError:
                    print("User does not exist.")

                server_socket.sendto(south_room.encode(), client_address)

        elif message.decode() == "west":
            if west_room is None:
                server_socket.sendto(OPERATION_FAILURE.encode(), client_address)
            else:

                # Tell the rest of the server that X-player left.
                for player in room.players:
                    address = player.split(',')
                    port_num = address[1].split('-')
                    port_num[0] = port_num[0].strip('()')

                    if int(parsed_port) != int(port_num[0]):
                        name = room.get_player_name_by_port(int(parsed_port))

                        new_message = name + " left the room, heading west.\n"

                        server_socket.sendto(new_message.encode(), ("127.0.0.1", int(port_num[0])))

                # Remove player from current server.
                try:
                    # Remove the player with the same format they were added to player list.
                    player_to_remove = str(client_address) + "-" + room.get_player_name_by_port(int(parsed_port))

                    room.players.remove(player_to_remove)
                    print("User moved west: ", str(client_address))
                except ValueError:
                    print("User does not exist.")

                server_socket.sendto(west_room.encode(), client_address)

        elif message.decode() == "up":
            if up_room is None:
                server_socket.sendto(OPERATION_FAILURE.encode(), client_address)
            else:

                # Tell the rest of the server that X-player left.
                for player in room.players:
                    address = player.split(',')
                    port_num = address[1].split('-')
                    port_num[0] = port_num[0].strip('()')

                    if int(parsed_port) != int(port_num[0]):
                        name = room.get_player_name_by_port(int(parsed_port))

                        new_message = name + " left the room, heading up.\n"

                        server_socket.sendto(new_message.encode(), ("127.0.0.1", int(port_num[0])))

                # Remove player from current server.
                try:
                    # Remove the player with the same format they were added to player list.
                    player_to_remove = str(client_address) + "-" + room.get_player_name_by_port(int(parsed_port))

                    room.players.remove(player_to_remove)
                    print("User moved up: ", str(client_address))
                except ValueError:
                    print("User does not exist.")

                server_socket.sendto(up_room.encode(), client_address)

        elif message.decode() == "down":
            if down_room is None:
                server_socket.sendto(OPERATION_FAILURE.encode(), client_address)
            else:

                # Tell the rest of the server that X-player left.
                for player in room.players:
                    address = player.split(',')
                    port_num = address[1].split('-')
                    port_num[0] = port_num[0].strip('()')

                    if int(parsed_port) != int(port_num[0]):
                        name = room.get_player_name_by_port(int(parsed_port))

                        new_message = name + " left the room, heading down.\n"

                        server_socket.sendto(new_message.encode(), ("127.0.0.1", int(port_num[0])))

                # Remove player from current server.
                try:
                    # Remove the player with the same format they were added to player list.
                    player_to_remove = str(client_address) + "-" + room.get_player_name_by_port(int(parsed_port))

                    room.players.remove(player_to_remove)
                    print("User moved down: ", str(client_address))
                except ValueError:
                    print("User does not exist.")

                server_socket.sendto(down_room.encode(), client_address)

        elif message.decode().find("exit") != -1:

            # Client will provide exit message with their name to exit.
            exit_info = message.decode().split(',')

            # Remove from player list
            try:
                # Remove the player with the same format they were added to player list.
                player_to_remove = str(client_address) + "-" + exit_info[1]

                for player in room.players:
                    address = player.split(',')
                    port_num = address[1].split('-')
                    port_num[0] = port_num[0].strip('()')

                    if int(parsed_port) != int(port_num[0]):
                        name = room.get_player_name_by_port(int(parsed_port))

                        new_message = name + " has left the game completely.\n"

                        server_socket.sendto(new_message.encode(), ("127.0.0.1", int(port_num[0])))

                room.players.remove(player_to_remove)
                print("User disconnected: ", str(client_address))

            except ValueError:
                print("User does not exist.")


if __name__ == "__main__":
    main()