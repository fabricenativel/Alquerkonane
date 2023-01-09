from dataclasses import dataclass


SIZE = 3
LINE_NUMBER = 2
MOVES_BLACK = [(-1,-1),(-1,1)]
MOVES_WHITE = [(1,-1),(1,1)]
TAKES  = [(0,2),(0,-2),(2,0),(-2,0)]



@dataclass(frozen=True,slots=True)
class GameState:
    '''Un état du jeu d'alquerkonane', les attributs sont les coordonnées des pions noirs/blancs et un booléen indiquant si les c'est le tour des noirs'''
    white : frozenset
    black : frozenset
    black_plays : bool

    def get_moves(self):
        '''renvoie la liste des mouvements possibles pour un etat de jeu sous la forme d'un ensemble de tuples (un triplet pour une prise, un couple pour un mouvement)'''
        possible_moves = set()
        if self.black_plays:
            pawns, ennemies, moves = self.black, self.white, MOVES_BLACK
        else:
            pawns, ennemies, moves = self.white, self.black, MOVES_WHITE
        for l,c in pawns:
            # déplacements possibles
            for dl,dc in moves:
                if on_board(l+dl,c+dc) and (l+dl,c+dc) not in self.white | self.black:
                    possible_moves.add(((l+dl,c+dc),(l,c)))
            # prises possibles
            for dl,dc in TAKES:
                if on_board(l+dl,c+dc) and (l+dl//2,c+dc//2) in ennemies and (l+dl,c+dc) not in self.white | self.black:
                    possible_moves.add(((l+dl,c+dl),(l,c),(l+dl//2,c+dc//2)))
        return possible_moves

    def __str__(self):
        return f"coordonnées des blancs : {self.white} \ncoordonnées des noirs : {self.black}"
    
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
            return GameState(new_ennemies,frozenset(new_pawns),False)
        else:
            return GameState(frozenset(new_pawns),new_ennemies,True)
            
    
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


def on_board(i,j):
    return 0<=i<SIZE and 0<=j<SIZE

def get_start(size):
    white = frozenset({(SIZE-i-1,j+i%2) for j in range(0,size,2) for i in range(LINE_NUMBER)})
    black = frozenset({(i,j+i%2) for j in range(0,SIZE,2) for i in range(LINE_NUMBER)}) 
    return GameState(white,black,True)

start = get_start(SIZE)
print(start)
print(start.winner())