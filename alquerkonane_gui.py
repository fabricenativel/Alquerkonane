from dataclasses import dataclass
from functools import lru_cache
import PySimpleGUI as sg
from time import perf_counter

'''
La case en haut et à gauche est (0,0)
on donne l'indice de LIGNE ne premier et l'indice de COLONNE en deuxième
'''

SIZE = 4
LINE_NUMBER = 2
BLACK_START = False

GET_WINNER = True

MOVES_BLACK = [(1,-1),(1,1)]
MOVES_WHITE = [(-1,-1),(-1,1)]
TAKES  = [(0,2),(0,-2),(2,0),(-2,0)]
WHITE_PAWN, BLACK_PAWN = "white_pawn.png","black_pawn.png"
WHITE_EMPTY, BLACK_EMPTY = "white.png", "black.png"
WHITE_SELECTED, BLACK_SELECTED = "white_selected.png","black_selected.png"
WHITE_LANDING, BLACK_LANDING = "white_landing.png","black_landing.png"

PLAYER = chr(0x25B6)
WINNER = chr(0x2605)

@dataclass(frozen=True)
class GameState:
    '''Un état du jeu d'alquerkonane', les attributs sont les coordonnées des pions noirs/blancs et un booléen indiquant si les c'est le tour des noirs'''
    white : frozenset
    black : frozenset
    black_plays : bool

    def get_moves(self):
        '''renvoie la liste des mouvements possibles pour un état de jeu sous la forme d'un ensemble de tuples (un triplet pour une prise, un couple pour un mouvement). Le premier élément du tuple est le nouvel emplacement du pion. L'autre (ou les deux autres) sont les pions qui disparaissent suite au mouvement'''
        possible_moves = set()
        if self.black_plays:
            pawns, ennemies, moves = self.black, self.white, MOVES_BLACK
        else:
            pawns, ennemies, moves = self.white, self.black, MOVES_WHITE
        for l,c in pawns:
            # déplacements possibles
            for dl,dc in moves:
                if dans_grille(l+dl,c+dc) and (l+dl,c+dc) not in self.white | self.black:
                    possible_moves.add(((l+dl,c+dc),(l,c)))
            # prises possibles
            for dl,dc in TAKES:
                if dans_grille(l+dl,c+dc) and (l+dl//2,c+dc//2) in ennemies and (l+dl,c+dc) not in self.white | self.black:
                    possible_moves.add(((l+dl,c+dc),(l,c),(l+dl//2,c+dc//2)))
        return possible_moves

    def get_moves_from(self,l,c):
        '''Renvoie la liste des mouvements possibles depuis le pion situé en (l,c)'''
        possible_moves = set()
        if self.black_plays:
            ennemies, moves =  self.white, MOVES_BLACK
        else:
            ennemies, moves =  self.black, MOVES_WHITE
        for dl,dc in moves:
            if dans_grille(l+dl,c+dc) and (l+dl,c+dc) not in self.white | self.black:
                possible_moves.add(((l+dl,c+dc),(l,c)))
            # prises possibles
        for dl,dc in TAKES:
            if dans_grille(l+dl,c+dc) and (l+dl//2,c+dc//2) in ennemies and (l+dl,c+dc) not in self.white | self.black:
                possible_moves.add(((l+dl,c+dc),(l,c),(l+dl//2,c+dc//2)))
        return possible_moves

    def __str__(self):
        return f"coordonnées des blancs : {self.white} \n coordonnées des noirs : {self.black}"

    
    def play(self,move):
        ''' Génération d'un nouvel état du jeu en jouant un coup'''
        if self.black_plays:
            pawns, ennemies = self.black, self.white
        else:
            pawns, ennemies = self.white, self.black
        new_pawns = set(pawns - {move[1]})
        new_pawns.add(move[0])
        if len(move)==3:
            new_ennemies = ennemies - {move[2]}
        else:
            new_ennemies = ennemies.copy()
        if self.black_plays:
            return GameState(frozenset(new_ennemies),frozenset(new_pawns),False)
        else:
            return GameState(frozenset(new_pawns),frozenset(new_ennemies),True)
    
    def undo(self,move):
        if self.black_plays:
            pawns, ennemies = self.white, self.black
        else:
            pawns, ennemies = self.black, self.white
        new_pawns = set(pawns-{move[0]})
        new_pawns.add(move[1])
        if len(move)==3:
            new_ennemies = set(ennemies)
            new_ennemies.add(move[2])
        else:
            new_ennemies = ennemies.copy()
        if self.black_plays:
            return GameState(frozenset(new_pawns),frozenset(new_ennemies),False)
        else:
            return GameState(frozenset(new_ennemies),frozenset(new_pawns),True)

    @lru_cache(maxsize=None)
    def winner(self):
        moves = self.get_moves()
        if self.black_plays:
            cp, op = "black","white"
        else:
            cp, op = "white","black"
        if len(moves)==0:
            return op
        to_search = set()
        for m in moves:
            next_state = self.play(m)
            if len(next_state.get_moves())==0: 
                return cp
            to_search.add(next_state)
        if all(n.winner()==op for n in to_search):
            return op
        return cp

class Alquerkonane:

    def __init__(self, size):
        textleft = sg.Text("",key='tleft',size=(15,1),justification='l')
        textright = sg.Text("",key='tright',size=(15,1),justification='r')
        top = [[sg.Button('',key=f'({lig},{col})',pad=(0,0)) for col in range(size)] for lig in range(size)]
        bottom =[[sg.Button("Undo"),sg.Button("Reset"),sg.Button("Exit")]]
        layout = [[textleft,sg.Stretch(),textright],[sg.HSeparator()],[top],[sg.HSeparator()],[bottom]]
        self.size = size
        self.view = sg.Window('Alquerkonane', layout,finalize=True)
        self.state = get_start(size)
        self.selected = None # pour l'UI: indique donne les coordonnées du pion sélectionné
        self.landing = set() # pour l'UI : atterrissage possible d'un pion sélectionné
        self.history = []
        self.set_position()
        
    
    def reset(self,size):
        self.state = get_start(size)
        self.selected = None # pour l'UI: indique donne les coordonnées du pion sélectionné
        self.landing = set() # pour l'UI : atterrissage possible d'un pion sélectionné
        self.set_position()
        self.history = []

    def set_position(self):
        content = {(lig,col):WHITE_EMPTY if (lig+col)%2==1 else BLACK_EMPTY for lig in range(self.size) for col in range(self.size)}
        for l,c in self.state.white:
            content[(l,c)] = WHITE_PAWN
        for l,c in self.state.black:
            content[(l,c)] = BLACK_PAWN
        for l,c in content:
            self.view[f'({l},{c})'].Update(image_filename=content[(l,c)])
        self.set_text()
        
    def set_text(self):
        if self.state.black_plays:
            wp,bp = " ",PLAYER
        else:
            wp,bp = PLAYER," "
        if GET_WINNER:
            if self.state.winner()=="white":
                ww,bw = WINNER," "
            else:
                ww,bw = " ",WINNER
        else:
            ww,bw = "-","-"
        self.view['tleft'].Update(f"{wp} White : {len(self.state.white)} {ww}")
        self.view['tright'].Update(f"{bp} Black : {len(self.state.black)} {bw}")
    
    def end(self):
        if self.state.black_plays:
            w = "white"
        else:
            w = "black"
        self.view['tleft'].Update(f"{w} player wins")
        self.view['tright'].Update(f"")

    
    def select(self,l,c):
        if (l,c) in self.state.white:
            select_img = WHITE_SELECTED
            land_img = WHITE_LANDING
        else:
            select_img = BLACK_SELECTED
            land_img = BLACK_LANDING
        self.view[f'({l},{c})'].Update(image_filename=select_img)
        for m in self.state.get_moves_from(l,c):
            ll,cc = m[0]
            self.view[f'({ll},{cc})'].Update(image_filename=land_img)
        self.selected = (l,c)
        self.landing = {x[0] for x  in self.state.get_moves_from(l,c)}

    
    def deselect(self):
        if self.selected in self.state.white:
            deselect_img = WHITE_PAWN
            tile_img = WHITE_EMPTY
        else:
            deselect_img = BLACK_PAWN
            tile_img = BLACK_EMPTY
        l,c = self.selected
        self.view[f'({l},{c})'].Update(image_filename=deselect_img)
        for m in self.state.get_moves_from(l,c):
            ll,cc = m[0]
            self.view[f'({ll},{cc})'].Update(image_filename=tile_img)
        self.selected = None
        self.landing = set()
    
    def do_move(self,l,c):
        for m in self.state.get_moves_from(*game.selected):
            if m[0]==(l,c):
                break
        if self.selected in self.state.white:
            pawn_img = WHITE_PAWN
            tile_img = WHITE_EMPTY
            tile_kill = BLACK_EMPTY
        else:
            pawn_img = BLACK_PAWN
            tile_img = BLACK_EMPTY
            tile_kill = WHITE_EMPTY
        self.view[f'({l},{c})'].Update(image_filename=pawn_img)
        self.view[f'({m[1][0]},{m[1][1]})'].Update(image_filename=tile_img)
        if len(m)==3:
            self.view[f'({m[2][0]},{m[2][1]})'].Update(image_filename=tile_kill)
        for x in self.landing-{(l,c)}:
            ll,cc = x
            self.view[f'({ll},{cc})'].Update(image_filename=tile_img)
        self.selected, self.landing = None,set()
        self.state = self.state.play(m)
        self.history.append(m)
        self.set_text()
        if len(game.state.get_moves())==0:
            game.end()
    
    def undo_move(self):
        if self.state.black_plays:
            pawn_img = WHITE_PAWN
            tile_img = WHITE_EMPTY
            pawn_kill = BLACK_PAWN
        else:
            pawn_img = BLACK_PAWN
            tile_img = BLACK_EMPTY
            pawn_kill = WHITE_PAWN
        if self.history!=[]:
            move = self.history.pop()
            self.view[f'({move[0][0]},{move[0][1]})'].Update(image_filename=tile_img)
            self.view[f'({move[1][0]},{move[1][1]})'].Update(image_filename=pawn_img)
            if len(move)==3:
                self.view[f'({move[2][0]},{move[2][1]})'].Update(image_filename=pawn_kill)
            self.state = self.state.undo(move)
            self.set_text()


def dans_grille(i,j):
    return 0<=i<SIZE and 0<=j<SIZE

def get_start(size):
    if size%2 == 0:
        white = frozenset({(SIZE-i-1,j+i%2) for j in range(0,size,2) for i in range(LINE_NUMBER)})
        black = frozenset({(i,j+i%2) for j in range(0,SIZE,2) for i in range(LINE_NUMBER)}) 
    else:
        white = frozenset({(SIZE-i-1,j+i%2-1) for j in range(0,size,2) for i in range(LINE_NUMBER) if size>j+i%2-1>=0 })
        black = frozenset({(i,j+i%2) for j in range(0,SIZE,2) for i in range(LINE_NUMBER) if size>j+i%2>=0}) 
    return GameState(white,black,BLACK_START)

def conversion(event):
    levent = event[1:-1].split(",")
    return int(levent[0]),int(levent[1])


game = Alquerkonane(SIZE)
if GET_WINNER:
    start =  perf_counter()
    print("La position est gagnante pour ",game.state.winner())
    print(f"Calcul en {perf_counter()-start} sec")
exit = False
while not exit:
    event, values = game.view.read()
    if event=='Exit' or event==sg.WIN_CLOSED:
        game.view.Close()
        exit = True
    elif event=='Reset':
        game.reset(SIZE)
    elif event=='Undo':
        game.undo_move()
    elif game.selected==None and ((conversion(event) in game.state.black and game.state.black_plays) or (conversion(event) in game.state.white and not game.state.black_plays)):
        # Selection d'un pion
            game.select(*conversion(event))
        # Déselection d'un pion
    elif game.selected!=None and game.selected == conversion(event):
            game.deselect()
        # Mouvement d'un pion
    elif game.selected!=None and (conversion(event) in game.landing):
            game.do_move(*conversion(event))
            