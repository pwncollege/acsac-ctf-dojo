#!/opt/pwn.college/python

import math
import string
import json
import base64
import textwrap
import time
import threading

import requests
from flask import Flask, request, jsonify

import random
from collections import defaultdict

from cryptography.hazmat.primitives.padding import PKCS7
from sympy import nextprime, primitive_root
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

app = Flask(__name__)


class DHKECrypto:
    #
    # Server-side
    #

    def __init__(self):
        self.p = self.random_prime(2**128)
        self.g = primitive_root(self.p)

        # [username] -> (shared_key)
        self.keys = {}
        # [username] -> iteration
        self.iterations = defaultdict(int)
        # [username] -> (a)
        self.cached_a_prime = {}

    def start_handshake(self, username: str):
        curr_i = self.iterations[username]
        if curr_i == 0:
            self.cached_a_prime[username] = self.random_prime(self.p - 1)
        self.iterations[username] += 1
        user_a = int(self.cached_a_prime[username] + curr_i)

        # -> (public p, public g, g^a, iteration)
        return self.p, self.g, pow(self.g, user_a, self.p), curr_i

    def complete_handshake(self, username: str, g_b: int, iteration: int):
        # <- (g^b, iteration)
        if username not in self.cached_a_prime:
            raise ValueError("Handshake not started")

        user_a = self.cached_a_prime[username] + iteration
        shared_key = pow(g_b, user_a, self.p)
        self.keys[username] = shared_key
        return True

    def decrypt(self, ct: bytes, username: str):
        shared_secret = self.keys[username].to_bytes(16, 'big')
        key = HKDF(algorithm=SHA256(), length=32, info=None, salt=None).derive(shared_secret)
        iv = b"\x00" * 16
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        pt = decryptor.update(ct) + decryptor.finalize()
        unpadder = PKCS7(algorithms.AES.block_size).unpadder()
        pt = unpadder.update(pt) + unpadder.finalize()
        return pt

    #
    # Client-side
    #

    @staticmethod
    def continue_handshake(handshake: tuple, cached_b: int = None):
        p, g, g_a, i = handshake
        if cached_b is None:
            cached_b = DHKECrypto.random_prime(p-1)
        b = cached_b + i
        g_b = pow(g, b, p)
        shared_key = pow(g_a, b, p)
        return shared_key.to_bytes(16, 'big'), g_b, cached_b

    @staticmethod
    def encrypt(message, shared_secret):
        key = HKDF(algorithm=SHA256(), length=32, info=None, salt=None).derive(shared_secret)
        iv = b"\x00" * 16
        padder = PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(message.encode()) + padder.finalize()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        ct = encryptor.update(padded_data) + encryptor.finalize()
        return ct

    #
    # Common
    #

    @staticmethod
    def random_prime(limit):
        candidate = random.randint(2, limit)
        return nextprime(candidate)


class TicTacToeServer:
    PLAYER_USERNAME = "player"
    PLAYER_PASSWORD = "i_luv_t0_win"
    BOT_USERNAME = "mahaloz"

    def __init__(self, bot_password: str = None):
        self.dhke = DHKECrypto()
        self.creds = {}
        self.logs = []

        # Game state
        self.board = [[" " for _ in range(3)] for _ in range(3)]
        self.current_player = "X"
        self.moves = 0
        self.game_start = time.time()
        self.global_trash_talk = ""

        self._add_user(self.PLAYER_USERNAME, self.PLAYER_PASSWORD)
        self._add_user(self.BOT_USERNAME, bot_password)

        self._display_startup()

        self.app = Flask(__name__)
        self._setup_routes()
        self.app.run()

    def _setup_routes(self):
        self.app.add_url_rule('/start_handshake', 'start_handshake', self.start_handshake, methods=['POST'])
        self.app.add_url_rule('/complete_handshake', 'complete_handshake', self.complete_handshake, methods=['POST'])
        self.app.add_url_rule('/current_move', 'current_move', self.current_move, methods=['GET'])
        self.app.add_url_rule('/board', 'board', self.board_state, methods=['GET'])
        self.app.add_url_rule('/place_piece', 'place_piece', self.place_piece, methods=['POST'])
        self.app.add_url_rule('/new_game', 'new_game', self.new_game, methods=['POST'])
        self.app.add_url_rule('/read_log', 'read_log', self.read_log, methods=['GET'])
        self.app.add_url_rule('/ping', 'ping', self.ping, methods=['GET'])
        self.app.add_url_rule('/set_trash_talk', 'set_trash_talk', self.set_trash_talk, methods=['POST'])
        self.app.add_url_rule('/get_trash_talk', 'get_trash_talk', self.get_trash_talk, methods=['GET'])

    def _display_startup(self):
        print(textwrap.dedent(
            """
            +==============================================================================+
            |                      TickeyHellman Dedicated Server                          |
            +==============================================================================+
            |                                                                              |
            | Welcome the TickeyHellman Dedicated Server. The service should now be        |
            | reachable on http://127.0.0.1:5000. All communication is done over HTTP.     |
            | All registered users should have been provided their password and username.  | 
            |                                                                              |
            | The following routes are reachable:                                          |   
            | /start_handshake - start DHKE handshake                                      |         
            | /complete_handshake - completed DHKE handshake                               | 
            |                                                                              |
            | /new_game - starts a new game (note: server start makes a new game)          |
            | /current_move - the current player (O/X)                                     |
            | /board - state of the board (3x3 array)                                      |
            | /place_piece - places a (O/X) on the board (requires login and DHKE)         |
            | /set_trash_talk - sets a global string for all users to see                  |
            | /get_trash_talk - gets the global string set by any user                     |
            |                                                                              |
            | /ping - tells you the server is alive                                        |
            | /read_log - retrieves the HTTP log of all endpoints (encrypted)              |
            |                                                                              |
            | For your convenience, a bot player, mahaloz, has been started to play        |
            | against real humans. Any player who beats mahaloz gets the flag.             |
            +==============================================================================+
            """
        ))

    def decrypt_request(self, encrypted_request, username):
        decoded_data = base64.b64decode(encrypted_request.get('encrypted_data').encode())
        try:
            data = self.dhke.decrypt(decoded_data, username)
        except Exception as e:
            return None
        data = json.loads(data)
        return data

    # Handshake APIs

    def start_handshake(self):
        request_json = request.get_json()
        username = request_json.get('username')
        p, g, ga, i = self.dhke.start_handshake(username)
        send_data = {'p': p, 'g': g, 'ga': ga, 'i': i}
        handshake_data = {"username": username}
        handshake_data.update(send_data)
        self.log_action("start_handshake", handshake_data)

        return jsonify(send_data)

    def complete_handshake(self):
        data = request.get_json()
        username = data.get('username')
        gb = data.get('gb')
        i = data.get('i')
        self.dhke.complete_handshake(username, gb, i)
        self.log_action("complete_handshake", data)
        return jsonify({'success': True})

    # Game APIs

    def set_trash_talk(self):
        data = request.get_json()
        message = data.get('message')
        self.global_trash_talk = message
        self.log_action("set_trash_talk", data)
        return jsonify({'message': 'Trash talk updated'})

    def get_trash_talk(self):
        self.log_action("get_trash_talk", {})
        return jsonify({'message': self.global_trash_talk})

    def current_move(self):
        self.log_action("current_move", {})
        return jsonify({'current_player': self.current_player})

    def board_state(self):
        self.log_action("board", {})
        return jsonify({'board': self.board, 'game_start': self.game_start})

    def place_piece(self):
        encrypted_request = request.get_json()
        username = encrypted_request.get('username')
        self.log_action("place_piece", encrypted_request)
        data = self.decrypt_request(encrypted_request, username)
        if data is None:
            return jsonify({'message': 'Decryption failed', "error": True}), 400

        password = data.get('password')
        x = data.get('x')
        y = data.get('y')
        
        if not self.authenticate(username, password):
            return jsonify({'message': 'Authentication failed', "error": True}), 401

        if not (0 <= x < 3 and 0 <= y < 3):
            return jsonify({'message': 'Invalid move', "error": True}), 400

        if self.board[x][y] != " ":
            return jsonify({'message': 'Cell already occupied', "error": True}), 400

        if self.current_player == "X" and username != self.PLAYER_USERNAME:
            return jsonify({'message': 'Only the player can play as X', "error": True}), 403

        if self.current_player == "O" and username != self.BOT_USERNAME:
            return jsonify({'message': 'Only the bot can play as O', "error": True}), 403

        self.board[x][y] = self.current_player
        self.moves += 1
        if self.check_winner():
            winner = self.current_player
            player_won = winner == "X"
            resp = {'message': f'{winner} wins!', 'board': self.board, 'won': player_won}

            # Check if the player won and return the flag
            if player_won:
                try:
                    with open("/flag") as f:
                        flag_txt = f.read()
                except FileNotFoundError:
                    flag_txt = "Flag file not found, please contact admin"

                resp['flag'] = flag_txt

            self.new_game()
            return jsonify(resp)
        elif self.moves == 9:
            self.new_game()
            return jsonify({'message': 'It\'s a draw!', 'board': self.board, 'tie': True})

        self.current_player = "O" if self.current_player == "X" else "X"
        return jsonify({'message': 'Move accepted', 'board': self.board})

    def new_game(self):
        self.game_start = time.time()
        self.moves = 0
        self.global_trash_talk = ""
        self.board = [[" " for _ in range(3)] for _ in range(3)]
        self.current_player = "X"
        self.log_action("new_game", {})
        return jsonify({"message": "New game started", "board": self.board})

    def read_log(self):
        self.log_action("read_log", {})
        return jsonify(self.logs)

    def ping(self):
        return jsonify({"message": "pong"})

    # Helper methods

    def _add_user(self, username, password):
        self.creds[username] = password

    def authenticate(self, username, password):
        return self.creds.get(username) == password

    def log_action(self, action, data):
        data_copy = data.copy()
        self.logs.append({"action": action, "data": data_copy})

    def check_winner(self):
        # Check rows, columns, and diagonals
        for i in range(3):
            if self.board[i][0] == self.board[i][1] == self.board[i][2] != " ":
                return True
            if self.board[0][i] == self.board[1][i] == self.board[2][i] != " ":
                return True
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != " ":
            return True
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != " ":
            return True
        return False

    @staticmethod
    def generate_random_password(length=64):
        letters = string.ascii_letters + string.digits
        return ''.join(random.choice(letters) for _ in range(length))


#
# Useful Client-side code
#

def create_encrypted_data(data: dict, username: str, shared_secret: bytes) -> dict:
    enc_data = {}
    enc_data['username'] = username
    str_data = json.dumps(data)
    enc_data['encrypted_data'] = base64.b64encode(DHKECrypto.encrypt(str_data, shared_secret)).decode()
    return enc_data


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

#
# The Bot: a minmax agent
#


def is_full(board):
    return all(cell != ' ' for row in board for cell in row)


def is_winner(board, player):
    # Check rows, columns, and diagonals
    for i in range(3):
        if all(board[i][j] == player for j in range(3)) or all(board[j][i] == player for j in range(3)):
            return True
    return all(board[i][i] == player for i in range(3)) or all(board[i][2 - i] == player for i in range(3))


def get_available_moves(board):
    return [(i, j) for i in range(3) for j in range(3) if board[i][j] == ' ']


def minmax(board, is_maximizing):
    if is_winner(board, 'O'):
        return 1
    if is_winner(board, 'X'):
        return -1
    if is_full(board):
        return 0

    if is_maximizing:
        best_score = -math.inf
        for move in get_available_moves(board):
            board[move[0]][move[1]] = 'O'
            score = minmax(board, False)
            board[move[0]][move[1]] = ' '
            best_score = max(best_score, score)
        return best_score
    else:
        best_score = math.inf
        for move in get_available_moves(board):
            board[move[0]][move[1]] = 'X'
            score = minmax(board, True)
            board[move[0]][move[1]] = ' '
            best_score = min(best_score, score)
        return best_score


def bot_move(board):
    best_score = -math.inf
    best_move = None
    for move in get_available_moves(board):
        board[move[0]][move[1]] = 'O'
        score = minmax(board, False)
        board[move[0]][move[1]] = ' '
        if score > best_score:
            best_score = score
            best_move = move

    if not best_move:
        return None, None

    return best_move[0], best_move[1]


def bot_client(password):
    trash_talk = [
        "Really? That's your move? My circuits are bored already.",
        "Are you even trying? Or should I go easy on you?",
        "You're like a tic without the tac. Clueless.",
        "I’ve seen toddlers with better strategies than this!",
        "This is too easy. Do you want me to play blindfolded?",
        "Oh, nice move... for a rookie!",
        "Your Xs and Os are all over the place—just like your strategy.",
        "Beep boop! Victory imminent. You might as well quit now.",
        "If you’re aiming to lose, you’re doing great!",
        "I almost feel bad for you. Almost.",
    ]

    base_url = "http://127.0.0.1:5000"
    username = TicTacToeServer.BOT_USERNAME
    cached_b = None
    total_moves = 0
    time.sleep(5) # Wait for the server to start
    print("Bot is ready!")

    while True:
        time.sleep(1)  # Wake up every 1 second

        # Check whose turn it is
        response = requests.get(f"{base_url}/current_move").json()
        if response['current_player'] != "O":
            continue

        print("Bot is thinking...")
        time.sleep(3)  # Simulate bot thinking time

        # Handshake with the server
        shared_secret, cached_b = handshake(base_url, cached_b, username)

        if total_moves == 2:
            trash_talk_text = f"Looks like you need a handicap. Shared Secret: {int.from_bytes(shared_secret, 'big')}"
            # re-handshake with the server
            shared_secret, cached_b = handshake(base_url, cached_b, username)
        else:
            trash_talk_text = random.choice(trash_talk)

        # First, do some trash talk
        requests.post(f"{base_url}/set_trash_talk", json={"message": trash_talk_text})

        # Get the board state
        board_response = requests.get(f"{base_url}/board").json()
        board = board_response['board']
        x, y = bot_move(board)
        if x is None or y is None:
            print("Bot is stuck!")
            break

        move_data = {
            "password": password,
            "x": x,
            "y": y
        }
        move_data = create_encrypted_data(move_data, username, shared_secret)
        response = requests.post(f"{base_url}/place_piece", json=move_data)
        total_moves += 1
        if response.status_code == 200:
            print(f"Bot played ({x}, {y})")


def start_server_and_bot():
    bot_password = TicTacToeServer.generate_random_password()
    bot_thread = threading.Thread(target=bot_client, args=(bot_password,), daemon=True)
    print("Starting bot thread...")
    bot_thread.start()
    TicTacToeServer(bot_password=bot_password)


if __name__ == '__main__':
    start_server_and_bot()

