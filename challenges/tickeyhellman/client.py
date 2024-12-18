import textwrap

import requests
import os
import time
from server import DHKECrypto, TicTacToeServer, create_encrypted_data


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def handshake(base_url, cached_b, username):
    handshake_resp = requests.post(f"{base_url}/start_handshake", json={"username": username}).json()
    p = handshake_resp['p']
    g = handshake_resp['g']
    ga = handshake_resp['ga']
    i = handshake_resp['i']
    _handshake = p, g, ga, i
    shared_secret, gb, cached_b = DHKECrypto.continue_handshake(_handshake, cached_b=cached_b)
    requests.post(f"{base_url}/complete_handshake", json={'username': username, 'gb': gb, 'i': i})
    return shared_secret, cached_b


def start_new_game(base_url):
    response = requests.post(f"{base_url}/new_game")
    print(response.json()["message"])
    input("\nPress Enter to continue...")
    clear_screen()


def print_board(board):
    print("\n  0   1   2")
    for i, row in enumerate(board):
        print(f"{i}  " + " | ".join(row))
        if i < 2:
            print("  ---+---+---")

def print_game_state(board, current_player, trash_talk):
    print("\nCurrent Board:")
    print_board(board)
    print("")
    print(f"Current Player: {current_player}")
    if trash_talk:
        print(f'{TicTacToeServer.BOT_USERNAME} says: "{trash_talk}"')
    print("")


def play_game(base_url, username, password, shared_secret):
    game_start = None
    tied = False
    last_board = None
    while True:
        # Display the board and current move
        board_response = requests.get(f"{base_url}/board").json()
        move_response = requests.get(f"{base_url}/current_move").json()
        trash_talk = requests.get(f"{base_url}/get_trash_talk").json()['message']
        current_player = move_response['current_player']

        # Check if lost
        curr_game_start = board_response['game_start']
        if game_start is None:
            game_start = curr_game_start
        elif game_start != curr_game_start:
            # game reset only happens when the bot wins or there's a tie
            if not tied:
                print_game_state(last_board, current_player, trash_talk)
                print("You lost! Better luck next time.")
                input("Press enter to continue...")
                clear_screen()
            game_start = curr_game_start
            tied = False

        board = board_response['board']
        last_board = board
        print_game_state(board, current_player, trash_talk)

        # Check if it's the player's turn
        if move_response['current_player'] == "X":
            user_input = input("Enter your move (row,col) or 'q' to quit: ")
            if user_input.lower() == 'q':
                break
            try:
                x, y = map(int, user_input.split(","))
                data = {"password": password, "x": x, "y": y}
                enc_data = create_encrypted_data(data, username, shared_secret)
                response = requests.post(f"{base_url}/place_piece", json=enc_data)
                resp_json = response.json()
                won = resp_json.get('won', None)
                tie = resp_json.get('tie', None)
                if response.status_code != 200 or won is True or tie is True or won is False:
                    if tie:
                        tied = True
                    print(resp_json['message'])
                    print("")
                    input("Press enter to continue...")
            except ValueError:
                print("Invalid input. Please enter in the format 'row,col'.")
        else:
            print(f"Waiting for {TicTacToeServer.BOT_USERNAME}'s move...")
            time.sleep(2)

        clear_screen()

def read_log(base_url):
    response = requests.get(f"{base_url}/read_log")
    log = response.json()
    print("\nLog:")
    for entry in log:
        print(entry)
    input("\nPress Enter to continue...")
    clear_screen()


def ping_server(base_url):
    try:
        response = requests.get(base_url+'/ping')
        if response.status_code == 200:
            return True
        else:
            return False
    except requests.exceptions.ConnectionError:
        return False


def display_start_banner():
    print(textwrap.dedent(
        """
        +==============================================================================+
        |                                 TickeyHellman                                |
        +==============================================================================+
        |                                                                              |
        | Welcome to TickeyHellman, the online, hyper-competitive, very secure,        |
        | Tic Tac Toe game -- secured using a novel and fast DHKE algorithm!           |
        |                                                                              |
        | Currently only supports 1v1: bot v player.                                   |
        | Beating the bot in any single match will get you the flag stored on the      |
        | server. Be advised: this bot is very good.                                   |
        |                                                                              |
        | The bot is playing in handicap mode. If you survive three moves, the bot     |
        | will give you a useful hint. Happy TicTacing!                                |
        +==============================================================================+
        """
    ))

def main():
    base_url = "http://127.0.0.1:5000"
    username = TicTacToeServer.PLAYER_USERNAME
    password = TicTacToeServer.PLAYER_PASSWORD

    server_online = ping_server(base_url)
    if not server_online:
        print("Server is not running. Please start the server and try again.")
        return

    shared_secret, cached_b = handshake(base_url, None, username)

    clear_screen()
    display_start_banner()
    while True:
        print("\nMenu:")
        print("1. New Game")
        print("2. Play...")
        print("3. Read Log")
        print("4. Exit")
        choice = input("Enter choice: ")

        if choice == "1":
            start_new_game(base_url)
        elif choice == "2":
            clear_screen()
            play_game(base_url, username, password, shared_secret)
            clear_screen()
        elif choice == "3":
            read_log(base_url)
        elif choice == "4":
            print("Exiting...")
            break
        else:
            print("Invalid choice!")
            input("\nPress Enter to continue...")
            clear_screen()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        exit(0)
