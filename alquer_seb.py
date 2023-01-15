"""
Jeu Alquerkonane
Variante à partir de la version de Fab
"""

from dataclasses import dataclass
from functools import lru_cache
import PySimpleGUI as sg
import argparse
from time import perf_counter

BLACK = 0
WHITE = 1

# Tuples d'infos... noir toujours en indice 0
#
BLACK_MOVES = (1, -1), (1, 1)
WHITE_MOVES = (-1, -1), (-1, 1)

MOVES = BLACK_MOVES, WHITE_MOVES
TAKES = (0, 2), (0, -2), (2, 0), (-2, 0)

PAWN_FILES = 'black_pawn.png', 'white_pawn.png'
EMPTY_FILES = 'black.png', 'white.png' 
SELECTED_FILES = 'black_selected.png', 'white_selected.png'
LANDING_FILES = 'black_landing.png', 'white_landing.png'

TURN_MARK = ('▶', ''), ('', '▶')
WINNING_MARK = ('★', ''), ('', '★')
RESULTS = ('wins', ''), ('', 'wins')

KEYS = 'Black', 'White'
ALIGN = 'lr'

# Aide des options

HELP_W = 'Largeur du damier, valeur par défaut 4'
HELP_H = 'Hauteur du damier, valeur par défaut 4'
HELP_L = 'Nombre de lignes de pions, 1 ou 2 (par défaut)'
HELP_WHO_START = "Identifiant du joueur qui commence : 0 = Black, 1 = White (par défaut)"
HELP_GET_WINNER = "Booléen ; si True le joueur gagnant est calculé et affiché dans les infos"


class View:

    def __init__(self, controller):
        self.ctrl = controller
        self.height = controller.height
        self.width = controller.width
        # ligne d'informations sur les joueurs noir / blanc : qui joue, qui est gagnant etc.
        top = [sg.Text("", key=KEYS[BLACK], size=(15,1), justification=ALIGN[BLACK]),
               sg.Text("", key=KEYS[WHITE], size=(15,1), justification=ALIGN[WHITE])]

        # la zone damier
        grid = [[sg.Button('', key=(lig, col), pad=(0, 0)) for col in range(self.width)] for lig in range(self.height)]

        # la zone menu
        menu =[sg.Button("Undo"), sg.Button("Reset"), sg.Button("Exit")]

        # le layout global
        layout = [[top[BLACK], sg.Stretch(), top[WHITE]],
                  [sg.HSeparator()],
                  [grid],
                  [sg.HSeparator()],
                  [menu]]
        
        # la fenêtre principale
        self.window = sg.Window('Alquerkonane', layout, finalize=True)

    def set_grid(self, i, j, filename):
        """Met à jour la vue de la case de coordonnée i, j avec le fichier image filename"""
        self.window[i, j].Update(image_filename=filename)

    def set_text(self, current_player_txt, current_winner_txt, counts):
        """Met à jour les textes en haut de la fenêtre
        current_player_txt vaut un des couple de la constante TURN_MARK
        current_winner_txt vaut un des couples de la constante WINNING_MARK ou '-', '-' si l'option n'a pas été choisie
        counts est un le couple des nombres de pions noirs et blancs
        """
        for player_id in (BLACK, WHITE):
            key = KEYS[player_id]  # clé au sens de sg
            turn_txt = current_player_txt[player_id]
            winner_txt = current_winner_txt[player_id]
            count = counts[player_id]
            self.window[key].Update(f'{turn_txt} {key} : {count} {winner_txt}')

    def close(self):
        self.window.Close()

    def read(self):
        event, _ = self.window.read()
        return event


class Model:

    def __init__(self, controller):
        self.controller = controller
        self.states = [self.initial_state(controller.player_start)]
        self.end = False

    def initial_state(self, player_id):
        height, width, lines = self.controller.game_size()
        if  height % 2 == 0:
            white = {(height-i-1, j + i%2) for j in range(0, width, 2) for i in range(lines) if width > j + i%2}
            black = {(i, j + i%2) for j in range(0, width, 2) for i in range(lines) if width > j + i%2} 
        else:
            white = {(height-i-1, j + i%2 - 1) for j in range(0, width+1, 2) for i in range(lines) if width > j + i%2 - 1 >= 0}
            black = {(i, j + i%2) for j in range(0, width, 2) for i in range(lines) if width > j + i%2 >=0}
        return GameState(width, height, frozenset(black), frozenset(white), player_id)

    def player(self):
        return self.states[-1].player

    def state(self):
        return self.states[-1]

    def scores(self):
        state = self.state()
        return len(state.black), len(state.white)

    def valid(self, i, j):
        state = self.state()
        player = state.player
        positions = state.black, state.white
        pawns, ennemies, moves = positions[player], positions[1 - player], MOVES[player]
        if (i, j) not in pawns:
            return False
        candidates = state.get_moves_from(i, j, ennemies, moves)
        return len(candidates) > 0

    def undo(self):
        if self.states:
            self.states.pop()

    def play(self, move):
        state = self.state().new_state(move)
        self.states.append(state)
        player = state.player
        positions = state.black, state.white
        if len(positions[player]) == 0 or len(state.get_moves()) == 0:
            self.end = True

    def get_moves_from(self, i, j):
        state = self.state()
        player = state.player
        positions = state.black, state.white
        ennemies, moves = positions[1 - player], MOVES[player]
        return state.get_moves_from(i, j, ennemies, moves)

    def winner(self):
        return self.state().winner()


@dataclass(frozen=True)
class GameState:
    """Un état du jeu d'alquerkonane', les attributs sont les coordonnées des pions noirs/blancs et un entier 0, 1 pour le joueur courant"""

    width: int
    height: int
    black: frozenset
    white: frozenset
    player: int

    def inside(self, i, j):
        return 0 <= i < self.height and 0 <= j < self.width

    def empty(self, i, j):
        return self.inside(i, j) and (i, j) not in self.black | self.white

    def get_moves(self):
        """renvoie la liste des mouvements possibles sous la forme d'un ensemble de triplets
        Le premier élément du triplet est le nouvel emplacement du pion. 
        Les deux autres sont les pions qui disparaissent suite au mouvement : le premier est donc l'ancienne
        position du pion qui bouge et le 2e est le pion adverse pris et donc peut-être à None si le mouvement n'est pas une prise
        """
        positions = self.black, self.white
        player = self.player
        possible_moves = set()
        pawns, ennemies, moves = positions[player], positions[1 - player], MOVES[player]
        for i, j in pawns:
            possible_moves |= self.get_moves_from(i, j, ennemies, moves)
        return possible_moves

    def get_moves_from(self, i, j, ennemies, moves):
        """renvoie la liste des mouvements possibles pour le pion en i, j sous la même forme que get_moves"""
        possible_moves = set()
        # déplacements possibles
        for di, dj in moves:
            end_i, end_j = i + di, j + dj
            if self.empty(end_i, end_j):
                possible_moves.add(((end_i, end_j), (i, j), None))

        # prises possibles
        for di, dj in TAKES:
            end_i, end_j = i + di, j + dj
            if self.empty(end_i, end_j) and (i + di//2, j + dj//2) in ennemies:
                possible_moves.add(((end_i, end_j), (i, j), (i+di//2, j+dj//2)))
        return possible_moves

    def new_state(self, move):
        ''' Génération d'un nouvel état du jeu en jouant un coup'''
        new_position, pawn_1, pawn_2 = move
        positions = self.black, self.white
        player = self.player
        pawns, ennemies = positions[player], positions[1 - player]
        new_pawns = pawns - {pawn_1} | {new_position} # frozenset 
        new_ennemies = ennemies - {pawn_2}            # frozenset 
        if player == BLACK:
            return GameState(self.width, self.height, new_pawns, new_ennemies, WHITE)
        else:
            return GameState(self.width, self.height, new_ennemies, new_pawns, BLACK)

    @lru_cache(maxsize=None)
    def winner(self):
        player = self.player
        moves = self.get_moves()
        if len(moves) == 0:
            return 1 - player
        states_to_explore = set()
        for m in moves:
            next_state = self.new_state(m)
            if len(next_state.get_moves()) == 0: 
                return player
            states_to_explore.add(next_state)
        if all(state.winner() == 1 - player for state in states_to_explore):
            return 1 - player
        return player


class Alquerkonane:
    """Le contrôleur : définir la taille du jeu (hauteur et largeur mais aussi si on a 1 ou 2 lignes
    embarque une vue (un pysimplegui window) et un modèle"""

    def __init__(self, width=4, height=4, lines=2):
        self.width = width
        self.height = height
        self.lines = lines if self.height > 2 else 1 # nombre de lignes de pions : 1 ou 2
        self.player_start = WHITE
        self.model = None # initialisé plus tard avec le setup
        self.view = None  # initialisé plus tard avec le setup
        self.get_winner = False
        self.future_winner = None
        self.end = False
        self.selected = None # pour l'UI: indique donne les coordonnées du pion sélectionné
        self.landing = {} # pour l'UI : atterrissage possible d'un pion sélectionné
        
    def setup(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-W', '--width', help=HELP_W, type=int)
        parser.add_argument('-H', '--height', help=HELP_H, type=int)
        parser.add_argument('-l', '--lines', help=HELP_L, type=int)
        parser.add_argument('-s', '--start', help=HELP_WHO_START)
        parser.add_argument('--win', help=HELP_GET_WINNER, action="store_true")

        args = parser.parse_args()
        if args.width:
            self.width = int(args.width)
        if args.height:
            self.height = int(args.height)
        if args.lines:
            self.lines = min(2, max(int(args.lines), 1))
        if self.height <= 2:
            self.lines = 1
        if args.start and args.start in '01':
            self.player_start = int(args.start)
        if args.win:
            self.get_winner = True
            
    def set_view(self, end=False):
        content = {(i, j): EMPTY_FILES[(i + j)%2] for i in range(self.height) for j in range(self.width)}
        state = self.model.state()
        player = state.player
        for player_id, positions in enumerate((state.black, state.white)):
            for i, j in positions:
                content[i, j] = PAWN_FILES[player_id]
        if self.selected is not None:
            content[self.selected] = SELECTED_FILES[player]
            for landing_position in self.landing:
                content[landing_position] = LANDING_FILES[player] 
        for i, j in content:
            self.view.set_grid(i, j, content[i, j])
        self.set_text(end)        

    def set_text(self, end):
        player = self.model.player()
        if end:
            current_positions_txt = '', ''
            future_winner_txt = RESULTS[1 - player]
        else:
            current_positions_txt = TURN_MARK[player]
            if self.future_winner is not None:
                future_winner_txt = WINNING_MARK[self.future_winner]
                self.future_winner = None
            else:
                future_winner_txt = '-', '-'
        self.view.set_text(current_positions_txt, future_winner_txt, self.model.scores())

    def reset(self):
        self.model = Model(self)
        self.set_view()
        self.selected = None # pour l'UI: indique les coordonnées du pion sélectionné
        self.landing = {} # pour l'UI : atterrissage possible d'un pion sélectionné

    def game_size(self):
        return self.width, self.height, self.lines

    def select(self, i, j):
        self.selected = i, j
        self.landing = {mv[0]: mv for mv in self.model.get_moves_from(i, j)}

    def deselect(self):
        self.selected = None
        self.landing = {}

    def handle_click(self, event):
        i, j = event 
        if self.selected is None and self.model.valid(i, j):
            self.select(i, j)
        elif self.selected is not None and self.selected == (i, j):
            self.deselect()
        elif self.selected is not None and (i, j) in self.landing:
            move = self.landing[i, j]
            self.model.play(move)
            self.future_winner = self.model.winner() if self.get_winner else None
            self.deselect()

    def loop(self):
        while not self.end:
            event = self.view.read()
            if event == 'Exit' or event == sg.WIN_CLOSED:
                self.view.close()
                self.end = True
            elif event == 'Reset':
                self.reset()
            elif not self.model.end:
                if event == 'Undo':
                    self.model.undo()
                    self.future_winner = self.model.winner() if self.get_winner else None
                else:
                    self.handle_click(event)
            self.set_view(self.model.end)

    def start(self):
        # initialisation du modèle et de la vue
        self.model = Model(self)
        t_start =  perf_counter()
        self.future_winner = self.model.winner()
        perf = perf_counter() - t_start
        print("La position est gagnante pour ", KEYS[self.future_winner])
        print(f"Calcul en {perf}s")
        self.view = View(self)
        self.set_view() 
     

game = Alquerkonane()
game.setup()
game.start()
game.loop()