# ─────────────────────────────────────────────
#  Quoridor — Logique du jeu (V6)
#  Gère : positions, déplacements, barrières,
#          BFS, compteur tours, historique coups
#  Zobrist hashing pour tables de transpositions
# ─────────────────────────────────────────────
from collections import deque
import random as _rnd
from constants import BOARD_SIZE, WALLS_PER_PLAYER

# ── Tables de Zobrist (initialisées une seule fois au chargement) ──────────
# Principe : chaque composante de l'état a un nombre aléatoire 64 bits.
# Le hash de l'état = XOR de tous les nombres actifs.
_rng = _rnd.Random(0xDEADBEEF)   # graine fixe → reproductible
_Z_POS   = [[[_rng.getrandbits(64) for _ in range(BOARD_SIZE)]
              for _ in range(BOARD_SIZE)]
             for _ in range(2)]          # [joueur][col][row]
_Z_HWALL = [[_rng.getrandbits(64) for _ in range(BOARD_SIZE - 1)]
             for _ in range(BOARD_SIZE - 1)]   # [row][col]
_Z_VWALL = [[_rng.getrandbits(64) for _ in range(BOARD_SIZE - 1)]
             for _ in range(BOARD_SIZE - 1)]   # [row][col]
_Z_TURN  = _rng.getrandbits(64)          # XORé quand c'est au joueur 1

_COLS = "abcdefghi"   # notation officielle Quoridor


class GameState:
    """État complet d'une partie de Quoridor."""

    def __init__(self):
        self.reset()

    # ── Initialisation ────────────────────────
    def reset(self):
        self.positions = [
            (4, 8),   # Joueur 0 (J1) — bas, veut atteindre row=0
            (4, 0),   # Joueur 1 (J2) — haut, veut atteindre row=8
        ]
        self.walls_left = [WALLS_PER_PLAYER, WALLS_PER_PLAYER]
        self.h_walls = [[False] * (BOARD_SIZE - 1) for _ in range(BOARD_SIZE - 1)]
        self.v_walls = [[False] * (BOARD_SIZE - 1) for _ in range(BOARD_SIZE - 1)]

        self.current    = 0      # 0 ou 1
        self.winner     = None   # None | 0 | 1
        self.move_mode  = True   # True=pion, False=barrière
        self.turn_count = 0      # nombre de coups joués
        self.history    = []     # [(joueur, notation), ...]
        self.selected_moves = []

        # ── Cache heuristique incrémentale ────
        self._bfs_cache = [None, None]   # [dist_j0, dist_j1]  None = invalide

        # ── Hash Zobrist ──────────────────────
        self._zobrist = (
            _Z_POS[0][4][8] ^ _Z_POS[1][4][0]
            # pas de murs, joueur 0 commence → _Z_TURN n'est pas XORé
        )

    # ── Hash Zobrist (lecture seule) ──────────
    @property
    def zobrist_hash(self) -> int:
        return self._zobrist

    # ── Accesseurs ────────────────────────────
    @property
    def current_pos(self):
        return self.positions[self.current]

    @property
    def opponent_pos(self):
        return self.positions[1 - self.current]

    # ── Notation Quoridor ─────────────────────
    @staticmethod
    def _pos_notation(col: int, row: int) -> str:
        """e5, a1, etc."""
        return f"{_COLS[col]}{BOARD_SIZE - row}"

    @staticmethod
    def _wall_notation(r: int, c: int, horizontal: bool) -> str:
        """e5h ou e5v  (coin supérieur-gauche de la barrière)."""
        suffix = "h" if horizontal else "v"
        return f"{_COLS[c]}{BOARD_SIZE - r}{suffix}"

    # ── BFS distance (avec cache incrémental) ─
    def bfs_distance(self, player: int) -> int:
        """Distance BFS depuis la position du joueur jusqu'à sa ligne de but.
        Résultat mis en cache — invalidé seulement si apply_move/apply_wall
        touche à ce joueur (heuristique incrémentale).
        """
        if self._bfs_cache[player] is not None:
            return self._bfs_cache[player]
        start    = self.positions[player]
        goal_row = 0 if player == 0 else BOARD_SIZE - 1
        visited  = {start}
        queue    = deque([(start, 0)])
        while queue:
            (col, row), dist = queue.popleft()
            if row == goal_row:
                self._bfs_cache[player] = dist
                return dist
            for dcol, drow in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nc, nr = col + dcol, row + drow
                if (nc, nr) in visited:
                    continue
                if not (0 <= nc < BOARD_SIZE and 0 <= nr < BOARD_SIZE):
                    continue
                if self._blocked(col, row, dcol, drow):
                    continue
                visited.add((nc, nr))
                queue.append(((nc, nr), dist + 1))
        self._bfs_cache[player] = 999
        return 999

    # ── Vérification de passage ───────────────
    def _blocked(self, col, row, dcol, drow) -> bool:
        c, r = col, row
        if drow == -1:
            if r == 0: return True
            if c < BOARD_SIZE - 1 and self.h_walls[r - 1][c]:    return True
            if c > 0              and self.h_walls[r - 1][c - 1]: return True
        elif drow == 1:
            if r == BOARD_SIZE - 1: return True
            if c < BOARD_SIZE - 1 and self.h_walls[r][c]:         return True
            if c > 0              and self.h_walls[r][c - 1]:      return True
        elif dcol == -1:
            if c == 0: return True
            if r < BOARD_SIZE - 1 and self.v_walls[r][c - 1]:     return True
            if r > 0              and self.v_walls[r - 1][c - 1]:  return True
        elif dcol == 1:
            if c == BOARD_SIZE - 1: return True
            if r < BOARD_SIZE - 1 and self.v_walls[r][c]:          return True
            if r > 0              and self.v_walls[r - 1][c]:       return True
        return False

    # ── Mouvements valides ────────────────────
    def valid_moves(self, player: int = None) -> list:
        if player is None:
            player = self.current
        col, row         = self.positions[player]
        opp_col, opp_row = self.positions[1 - player]
        moves = []
        for dcol, drow in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nc, nr = col + dcol, row + drow
            if not (0 <= nc < BOARD_SIZE and 0 <= nr < BOARD_SIZE):
                continue
            if self._blocked(col, row, dcol, drow):
                continue
            if (nc, nr) == (opp_col, opp_row):
                jc, jr = nc + dcol, nr + drow
                if (0 <= jc < BOARD_SIZE and 0 <= jr < BOARD_SIZE
                        and not self._blocked(nc, nr, dcol, drow)):
                    moves.append((jc, jr))
                else:
                    for sdcol, sdrow in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                        if (sdcol, sdrow) == (dcol, drow):
                            continue
                        sc, sr = nc + sdcol, nr + sdrow
                        if (0 <= sc < BOARD_SIZE and 0 <= sr < BOARD_SIZE
                                and not self._blocked(nc, nr, sdcol, sdrow)):
                            moves.append((sc, sr))
            else:
                moves.append((nc, nr))
        return moves

    # ── Appliquer un mouvement ────────────────
    def apply_move(self, col: int, row: int) -> bool:
        if (col, row) not in self.valid_moves():
            return False
        nota = self._pos_notation(col, row)
        self.history.append((self.current, nota))

        # Mise à jour Zobrist : retirer l'ancienne position, ajouter la nouvelle
        old_col, old_row = self.positions[self.current]
        self._zobrist ^= _Z_POS[self.current][old_col][old_row]
        self._zobrist ^= _Z_POS[self.current][col][row]
        # Changement de joueur
        self._zobrist ^= _Z_TURN

        self.positions[self.current] = (col, row)
        # Invalider cache BFS du joueur courant (son chemin a changé)
        self._bfs_cache[self.current] = None
        self.turn_count += 1

        if self.current == 0 and row == 0:
            self.winner = 0
        elif self.current == 1 and row == BOARD_SIZE - 1:
            self.winner = 1

        if self.winner is None:
            self.current = 1 - self.current
        self.selected_moves = []
        return True

    # ── BFS chemin libre ? ────────────────────
    def _has_path(self, player: int) -> bool:
        start    = self.positions[player]
        goal_row = 0 if player == 0 else BOARD_SIZE - 1
        visited  = {start}
        queue    = deque([start])
        while queue:
            col, row = queue.popleft()
            if row == goal_row:
                return True
            for dcol, drow in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nc, nr = col + dcol, row + drow
                if (nc, nr) in visited: continue
                if not (0 <= nc < BOARD_SIZE and 0 <= nr < BOARD_SIZE): continue
                if self._blocked(col, row, dcol, drow): continue
                visited.add((nc, nr))
                queue.append((nc, nr))
        return False

    # ── Valider + poser une barrière ──────────
    def can_place_wall(self, r: int, c: int, horizontal: bool) -> bool:
        if not (0 <= r < BOARD_SIZE - 1 and 0 <= c < BOARD_SIZE - 1):
            return False
        if self.walls_left[self.current] <= 0:
            return False
        if horizontal:
            if self.h_walls[r][c]: return False
            if c > 0              and self.h_walls[r][c - 1]: return False
            if c < BOARD_SIZE - 2 and self.h_walls[r][c + 1]: return False
            if self.v_walls[r][c]: return False
        else:
            if self.v_walls[r][c]: return False
            if r > 0              and self.v_walls[r - 1][c]: return False
            if r < BOARD_SIZE - 2 and self.v_walls[r + 1][c]: return False
            if self.h_walls[r][c]: return False

        if horizontal:
            self.h_walls[r][c] = True
        else:
            self.v_walls[r][c] = True
        ok = self._has_path(0) and self._has_path(1)
        if horizontal:
            self.h_walls[r][c] = False
        else:
            self.v_walls[r][c] = False
        return ok

    def apply_wall(self, r: int, c: int, horizontal: bool) -> bool:
        if not self.can_place_wall(r, c, horizontal):
            return False
        nota = self._wall_notation(r, c, horizontal)
        self.history.append((self.current, nota))
        if horizontal:
            self.h_walls[r][c] = True
            self._zobrist ^= _Z_HWALL[r][c]
        else:
            self.v_walls[r][c] = True
            self._zobrist ^= _Z_VWALL[r][c]
        # Un mur peut modifier les chemins des deux joueurs
        self._bfs_cache = [None, None]
        self.walls_left[self.current] -= 1
        self.turn_count += 1
        # Changement de joueur
        self._zobrist ^= _Z_TURN
        self.current = 1 - self.current
        return True

    # ── Infos panneau ─────────────────────────
    def panel_state(self) -> dict:
        if self.winner is not None:
            status = f"Joueur {self.winner + 1} a gagne !"
        elif self.move_mode:
            status = "Cliquez une case pour bouger"
        else:
            w = self.walls_left[self.current]
            status = f"Mode barriere — {w} restante{'s' if w != 1 else ''}"

        # 8 derniers coups pour l'historique affiché
        recent = self.history[-8:]

        return {
            'turn':       self.current + 1,
            'walls':      self.walls_left[:],
            'status':     status,
            'mode':       'move' if self.move_mode else 'wall',
            'turn_count': self.turn_count,
            'history':    recent,
            'dist':       [self.bfs_distance(0), self.bfs_distance(1)],
        }

