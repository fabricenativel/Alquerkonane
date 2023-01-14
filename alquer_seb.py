"""
Jeu Alquerkonane
Variante à partir de la version de Fab
"""

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

# Aide des options

HELP_W = 'Largeur du damier, valeur par défaut 4'
HELP_H = 'Hauteur du damier, valeur par défaut 4'
HELP_L = 'Nombre de lignes de pions, 1 ou 2 (par défaut)'
HELP_WHO_START = "Identifiant du joueur qui commence : 0 = Black, 1 = White (par défaut)"


class View:

    KEYS = 'Black', 'White'
    ALIGN = 'lr'

    def __init__(self, controller):
        self.ctrl = controller
        self.height = controller.height
        self.width = controller.width
        # ligne d'informations sur les joueurs noir / blanc : qui joue, qui est gagnant etc.
        top = [sg.Text("", key=View.KEYS[BLACK], size=(15,1), justification=View.ALIGN[BLACK]),
               sg.Text("", key=View.KEYS[WHITE], size=(15,1), justification=View.ALIGN[WHITE])]

        # la zone damier
        grid = [[sg.Button('', key=(lig, col), pad=(0, 0)) for col in range(self.width)] for lig in range(self.height)]

        # la zone menu
        menu =[[sg.Button("Undo"), sg.Button("Reset"), sg.Button("Exit"), sg.Button("Who wins?")]]

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
        for color in (BLACK, WHITE):
            key = View.KEYS[color]  # clé au sens de sg
            turn_txt = current_player_txt[color]
            winner_txt = current_winner_txt[color]
            count = counts[color]
            self.window[key].Update(f'{turn_txt} {key} : {count} {winner_txt}')

    def close(self):
        self.window.Close()

    def read(self):
        event, _ = self.window.read()
        return event


class Model:

    def __init__(self, controller):
        self.width = controller.width
        self.height = controller.height
        self.lines = controller.lines
        self.states = [self.initial_state(controller.player_start)]
        self.end = False

    def initial_state(self, player_id):
        height, width = self.height, self.width
        lines = self.lines
        if  height % 2 == 0:
            white = {(height-i-1, j + i%2) for j in range(0, width, 2) for i in range(lines)}
            black = {(i, j + i%2) for j in range(0, width, 2) for i in range(lines)} 
        else:
            white = {(height-i-1, j + i%2 - 1) for j in range(0, width+1, 2) for i in range(lines) if width > j + i%2 - 1 >= 0}
            black = {(i, j + i%2) for j in range(0, width, 2) for i in range(lines) if width > j + i%2 >=0}
        return GameState(black, white, player_id)

    def inside(self, i, j):
        return 0 <= i < self.height and 0 <= j < self.width

    def empty(self, i, j):
        state = self.states[-1]
        black, white = state.players
        return self.inside(i, j) and (i, j) not in black | white

    def player(self):
        return self.states[-1].player

    def counts(self):
        state = self.states[-1]
        return len(state.players[BLACK]), len(state.players[WHITE])

    def get_moves(self, state=None):
        """renvoie la liste des mouvements possibles pour un état de jeu sous la forme d'un ensemble de tuples 
        (un triplet pour une prise, un couple pour un mouvement). Le premier élément du tuple est le nouvel emplacement du pion. 
        L'autre (ou les deux autres) sont les pions qui disparaissent suite au mouvement
        """
        if state is None:
            state = self.states[-1]
        player = state.player
        possible_moves = set()
        pawns, ennemies, moves = state.players[player], state.players[1 - player], MOVES[player]
        for i, j in pawns:
            possible_moves |= self.get_moves_from(i, j, ennemies, moves)
        return possible_moves

    def get_moves_from(self, i, j, ennemies=None, moves=None):
        """renvoie la liste des mouvements possibles pour le pion en i, j sous la forme d'un ensemble de tuples 
        (un triplet pour une prise, un couple pour un mouvement). Le premier élément du tuple est le nouvel emplacement du pion. 
        Les deux autres (le 2e étant éventuellement None, None) sont les pions qui disparaissent suite au mouvement
        """
        if ennemies is None:
            state = self.states[-1]
            player = state.player
            ennemies, moves = state.players[1 - player], MOVES[player]

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

    def new_state(self, move, state):
        ''' Génération d'un nouvel état du jeu en jouant un coup'''
        new_position, pawn_1, pawn_2 = move
        player = state.player
        pawns, ennemies = state.players[player], state.players[1 - player]
        new_pawns = pawns - {pawn_1} | {new_position}
        new_ennemies = ennemies - {pawn_2}
        if player == BLACK:
            return GameState(new_pawns, new_ennemies, WHITE)
        else:
            return GameState(new_ennemies, new_pawns, BLACK)
    
    def valid(self, i, j):
        state = self.states[-1]
        player = state.player
        pawns, ennemies, moves = state.players[player], state.players[1 - player], MOVES[player]
        if (i, j) not in pawns:
            return False
        candidates = self.get_moves_from(i, j, ennemies, moves)
        return len(candidates) > 0
    
    def undo(self):
        if self.states:
            self.states.pop()

    def play(self, move):
        state = self.new_state(move, self.states[-1])
        self.states.append(state)
        player = state.player
        if len(state.players[player]) == 0 or len(self.get_moves(state)) == 0:
            self.end = True

    def last(self):
        return self.states[-1]

    @lru_cache(maxsize=None)
    def winner(self, state):
        player = state.player
        moves = self.get_moves(state)
        if len(moves) == 0:
            return 1 - player
        next_states = set()
        for m in moves:
            n_state = self.new_state(m, state)
            if len(self.get_moves(n_state)) == 0: 
                return player
            next_states.add(n_state)
        if all(self.winner(s) == 1 - player for s in next_states):
            return 1 - player
        return player


class GameState:
    """Un état du jeu d'alquerkonane', les attributs sont les coordonnées des pions noirs/blancs et un entier 0, 1 pour le joueur courant"""

    def __init__(self, black, white, player):
        self.players = frozenset(black), frozenset(white) 
        self.player = player


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
            
    def set_view(self, end=False):
        content = {(i, j): EMPTY_FILES[(i + j)%2] for i in range(self.height) for j in range(self.width)}
        state = self.model.states[-1]
        player = state.player
        for color in (BLACK, WHITE):
            for i, j in state.players[color]:
                content[i, j] = PAWN_FILES[color]
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
            current_players_txt = '', ''
            future_winner_txt = RESULTS[1 - player]
        else:
            current_players_txt = TURN_MARK[player]
            if self.future_winner is not None:
                future_winner_txt = WINNING_MARK[self.future_winner]
                self.future_winner = None
            else:
                future_winner_txt = '-', '-'
        counts = self.model.counts() 
        self.view.set_text(current_players_txt, future_winner_txt, counts)

    def reset(self):
        self.model = Model(self)
        self.set_view()
        self.selected = None # pour l'UI: indique les coordonnées du pion sélectionné
        self.landing = {} # pour l'UI : atterrissage possible d'un pion sélectionné

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
            self.deselect()

    def loop(self):
        while not self.end:
            event = self.view.read()
            if event == 'Exit' or event == sg.WIN_CLOSED:
                self.view.close()
                self.end = True
            elif event == 'Reset':
                self.reset()
            elif event == 'Who wins?':
                self.future_winner = self.model.winner(self.model.last())
            elif not self.model.end:
                if event == 'Undo':
                    self.model.undo()
                else:
                    self.handle_click(event)
            self.set_view(self.model.end)

    def start(self):
        # initialisation du modèle et de la vue
        self.model = Model(self)
        t_start =  perf_counter()
        self.future_winner = self.model.winner(self.model.last())
        perf = perf_counter() - t_start
        print("La position est gagnante pour ", View.KEYS[self.future_winner])
        print(f"Calcul en {perf}s")
        self.view = View(self)
        self.set_view() 
     

game = Alquerkonane()
game.setup()
game.start()
game.loop()