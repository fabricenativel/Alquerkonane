"""
Jeu Alquerkonane
Variante à partir de la version de Fab
"""

from functools import lru_cache
import PySimpleGUI as sg
import argparse
from time import perf_counter



SIZE = 4
LINE_NUMBER = 2
BLACK_START = False

GET_WINNER = False

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

# Aide des options

HELP_W = 'Largeur du damier, valeur par défaut 4'
HELP_H = 'Hauteur du damier, valeur par défaut 4'
HELP_L = 'Nombre de lignes de pions, 1 ou 2 (par défaut)'
HELP_WIN = "Calcule qui est le gagnant de l'état courant"


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
        menu =[[sg.Button("Undo"), sg.Button("Reset"), sg.Button("Exit")]]

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
        return self.window.read()


class Model:

    def __init__(self, controller):
        self.ctrl = controller
        self.width = controller.width
        self.height = controller.height
        self.lines = controller.lines
        self.states = [self.initial_state()]

    def initial_state(self):
        height, width = self.height, self.width
        lines = self.lines
        if  height % 2 == 0:
            white = frozenset({(height-i-1, j + i%2) for j in range(0, width, 2) for i in range(lines)})
            black = frozenset({(i, j + i%2) for j in range(0, width, 2) for i in range(lines)}) 
        else:
            white = frozenset({(height-i-1, j + i%2 - 1) for j in range(0, width+1, 2) for i in range(lines) if width > j + i%2 - 1 >= 0})
            black = frozenset({(i, j + i%2) for j in range(0, width, 2) for i in range(lines) if width > j + i%2 >=0}) 
        return GameState(black, white)

    def inside(self, i, j):
        return 0 <= i < self.height and 0 <= j < self.width

    def empty(self, i, j):
        black, white = self.players
        return self.inside(i, j) and (i, j) not in black | white

    def move_ok(self, end_i, end_j):
        return self.inside(end_i, end_j) and self.empty(end_i, end_j)
    
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
            # déplacements possibles
            for di, dj in moves:
                end_i, end_j = i + di, j + dj
                if self.empty(end_i, end_j):
                    possible_moves.add(((end_i, end_j), (i, j)))

            # prises possibles
            for di, dj in TAKES:
                end_i, end_j = i + di, j + dj
                if self.empty(end_i, end_j) and (i + di//2, j + dj//2) in ennemies:
                    possible_moves.add(((end_i, end_j), (i, j), (i+di//2, j+dj//2)))
        return possible_moves


class GameState:
    """Un état du jeu d'alquerkonane', les attributs sont les coordonnées des pions noirs/blancs et un entier 0, 1 pour le joueur courant"""

    def __init__(self, black, white):
        self.players = frozenset(black), frozenset(white) 
        self.player = BLACK

    def copy_by_move(self, i, j, end_i, end_j):
        pass

    def copy_by_take(self, i, j, end_i, end_j, taken_i, taken_j):
        pass


class Alquerkonane:
    """Le contrôleur : définir la taille du jeu (hauteur et largeur mais aussi si on a 1 ou 2 lignes
    embarque une vue (un pysimplegui window) et un modèle"""

    def __init__(self, width=4, height=4, lines=2, get_winner=False):
        self.width = width
        self.height = height
        self.lines = lines if self.height > 2 else 1 # nombre de lignes de pions : 1 ou 2
        self.get_winner = get_winner
        self.model = None # initialisé plus tard avec le setup
        self.view = None  # initialisé plus tard avec le setup
        self.end = False

        # pas utilisé pour l'instant
        self.selected = None # pour l'UI: indique donne les coordonnées du pion sélectionné
        self.landing = set() # pour l'UI : atterrissage possible d'un pion sélectionné
        self.history = []
        
    def setup(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-W', '--width', help=HELP_W, type=int)
        parser.add_argument('-H', '--height', help=HELP_H, type=int)
        parser.add_argument('-l', '--lines', help=HELP_L, type=int)
        parser.add_argument('--win', help=HELP_WIN, action="store_true")

        args = parser.parse_args()
        if args.width:
            self.width = int(args.width)
        if args.height:
            self.height = int(args.height)
        if args.lines:
            self.lines = min(2, max(int(args.lines), 1))
        if self.height <= 2:
            self.lines = 1
        if args.win:
            self.get_winner = True

        # initialisation du modèle et de la vue
        self.model = Model(self)
        self.view = View(self)
        self.set_view()        
            
    def set_view(self):
        content = {(i, j): EMPTY_FILES[(i + j)%2] for i in range(self.height) for j in range(self.width)}
        state = self.model.states[-1]
        for color in (BLACK, WHITE):
            for i, j in state.players[color]:
                content[i, j] = PAWN_FILES[color]
        for i, j in content:
            self.view.set_grid(i, j, content[i, j])
        self.set_text()        

    def set_text(self):
        current_players_txt = TURN_MARK[self.model.player()]
        if self.get_winner:
            current_winner_txt = WINNING_MARK[self.model.winner()]
        else:
            current_winner_txt = '-', '-'
        counts = self.model.counts() 
        self.view.set_text(current_players_txt, current_winner_txt, counts)

    def reset(self):
        self.model = Model(self)
        self.set_view()

        # pas utilisé pour l'instant
        self.selected = None # pour l'UI: indique donne les coordonnées du pion sélectionné
        self.landing = set() # pour l'UI : atterrissage possible d'un pion sélectionné
        self.history = []

    def loop(self):
        while not self.end:
            event, values = self.view.read()
            if event == 'Exit' or event == sg.WIN_CLOSED:
                self.view.close()
                self.end = True
            elif event == 'Reset':
                self.reset()
            # elif event=='Undo':
            #     game.undo_move()
            # elif game.selected==None and ((conversion(event) in game.state.black and game.state.black_plays) or (conversion(event) in game.state.white and not game.state.black_plays)):
            #     # Selection d'un pion
            #         game.select(*conversion(event))
            #     # Déselection d'un pion
            # elif game.selected!=None and game.selected == conversion(event):
            #         game.deselect()
            #     # Mouvement d'un pion
            # elif game.selected!=None and (conversion(event) in game.landing):
            #         game.do_move(*conversion(event))
            


        
    
#     def end(self):
#         if self.state.black_plays:
#             w = "white"
#         else:
#             w = "black"
#         self.view['tleft'].Update(f"{w} player wins")
#         self.view['tright'].Update(f"")

    
#     def select(self,l,c):
#         if (l,c) in self.state.white:
#             select_img = WHITE_SELECTED
#             land_img = WHITE_LANDING
#         else:
#             select_img = BLACK_SELECTED
#             land_img = BLACK_LANDING
#         self.view[f'({l},{c})'].Update(image_filename=select_img)
#         for m in self.state.get_moves_from(l,c):
#             ll,cc = m[0]
#             self.view[f'({ll},{cc})'].Update(image_filename=land_img)
#         self.selected = (l,c)
#         self.landing = {x[0] for x  in self.state.get_moves_from(l,c)}

    
#     def deselect(self):
#         if self.selected in self.state.white:
#             deselect_img = WHITE_PAWN
#             tile_img = WHITE_EMPTY
#         else:
#             deselect_img = BLACK_PAWN
#             tile_img = BLACK_EMPTY
#         l,c = self.selected
#         self.view[f'({l},{c})'].Update(image_filename=deselect_img)
#         for m in self.state.get_moves_from(l,c):
#             ll,cc = m[0]
#             self.view[f'({ll},{cc})'].Update(image_filename=tile_img)
#         self.selected = None
#         self.landing = set()
    
#     def do_move(self,l,c):
#         for m in self.state.get_moves_from(*game.selected):
#             if m[0]==(l,c):
#                 break
#         if self.selected in self.state.white:
#             pawn_img = WHITE_PAWN
#             tile_img = WHITE_EMPTY
#             tile_kill = BLACK_EMPTY
#         else:
#             pawn_img = BLACK_PAWN
#             tile_img = BLACK_EMPTY
#             tile_kill = WHITE_EMPTY
#         self.view[f'({l},{c})'].Update(image_filename=pawn_img)
#         self.view[f'({m[1][0]},{m[1][1]})'].Update(image_filename=tile_img)
#         if len(m)==3:
#             self.view[f'({m[2][0]},{m[2][1]})'].Update(image_filename=tile_kill)
#         for x in self.landing-{(l,c)}:
#             ll,cc = x
#             self.view[f'({ll},{cc})'].Update(image_filename=tile_img)
#         self.selected, self.landing = None,set()
#         self.state = self.state.play(m)
#         self.history.append(m)
#         self.set_text()
#         if len(game.state.get_moves())==0:
#             game.end()
    
#     def undo_move(self):
#         if self.state.black_plays:
#             pawn_img = WHITE_PAWN
#             tile_img = WHITE_EMPTY
#             pawn_kill = BLACK_PAWN
#         else:
#             pawn_img = BLACK_PAWN
#             tile_img = BLACK_EMPTY
#             pawn_kill = WHITE_PAWN
#         if self.history!=[]:
#             move = self.history.pop()
#             self.view[f'({move[0][0]},{move[0][1]})'].Update(image_filename=tile_img)
#             self.view[f'({move[1][0]},{move[1][1]})'].Update(image_filename=pawn_img)
#             if len(move)==3:
#                 self.view[f'({move[2][0]},{move[2][1]})'].Update(image_filename=pawn_kill)
#             self.state = self.state.undo(move)
#             self.set_text()


# def dans_grille(i,j):
#     return 0<=i<SIZE and 0<=j<SIZE

# def get_start(size):
#     if size%2 == 0:
#         white = frozenset({(SIZE-i-1,j+i%2) for j in range(0,size,2) for i in range(LINE_NUMBER)})
#         black = frozenset({(i,j+i%2) for j in range(0,SIZE,2) for i in range(LINE_NUMBER)}) 
#     else:
#         white = frozenset({(SIZE-i-1,j+i%2-1) for j in range(0,size,2) for i in range(LINE_NUMBER) if size>j+i%2-1>=0 })
#         black = frozenset({(i,j+i%2) for j in range(0,SIZE,2) for i in range(LINE_NUMBER) if size>j+i%2>=0}) 
#     return GameState(white,black,BLACK_START)

def conversion(event):
    levent = event[1:-1].split(",")
    return int(levent[0]),int(levent[1])


game = Alquerkonane()
game.setup()
game.loop()

# if GET_WINNER:
#     start =  perf_counter()
#     print("La position est gagnante pour ",game.state.winner())
#     print(f"Calcul en {perf_counter()-start} sec")
# exit = False
# while not exit:
#     event, values = game.view.read()
#     if event=='Exit' or event==sg.WIN_CLOSED:
#         game.view.Close()
#         exit = True
#     elif event=='Reset':
#         game.reset(SIZE)
#     elif event=='Undo':
#         game.undo_move()
#     elif game.selected==None and ((conversion(event) in game.state.black and game.state.black_plays) or (conversion(event) in game.state.white and not game.state.black_plays)):
#         # Selection d'un pion
#             game.select(*conversion(event))
#         # Déselection d'un pion
#     elif game.selected!=None and game.selected == conversion(event):
#             game.deselect()
#         # Mouvement d'un pion
#     elif game.selected!=None and (conversion(event) in game.landing):
#             game.do_move(*conversion(event))
            