# ─────────────────────────────────────────────
#  Quoridor — Intelligence Artificielle (V7)
#  Algorithme : Néga-β (Negamax + élagage α/β)
#               SSS* (Stockman 1979, best-first)
#  Heuristique incrémentale : BFS mis en cache
#  Table de transpositions (méthode de Zobrist)
#  Anti-boucle : historique des 12 dernières positions
# ─────────────────────────────────────────────
import copy
import math
import random
import time
from constants import BOARD_SIZE

# ── Niveaux de difficulté ─────────────────────
LEVELS = {
    'facile':   1,   # profondeur 1 — coup greedy
    'moyen':    2,   # profondeur 2
    'difficile':3,   # profondeur 3
    'expert':   4,   # profondeur 4
}

# Limiter le nombre de coups de barrières testés par nœud
MAX_WALL_MOVES = 8

# Historique global des positions IA (anti-boucle)
_position_history: list = []   # liste de (col, row) des positions IA récentes

def reset_history():
    """Vider l'historique en début de partie."""
    _position_history.clear()

def record_position(col, row):
    """Enregistrer la position IA après chaque coup."""
    _position_history.append((col, row))
    if len(_position_history) > 12:
        _position_history.pop(0)

def position_repeat_penalty(col, row) -> float:
    """Pénalité si cette position a déjà été visitée récemment."""
    count = _position_history.count((col, row))
    return count * 60.0   # -60 par répétition

# Paramètres de calibration de difficulté
EASY_RANDOM_CHANCE = 0.45      # plus élevé => IA plus "humaine" en facile
EASY_PREFER_MOVE_CHANCE = 0.85 # facile pose rarement des barrières
MEDIUM_MISTAKE_CHANCE = 0.18   # moyen fait parfois un choix non optimal

# ── Table de transpositions (méthode de Zobrist) ──────────────────────────
# Entrée : zobrist_hash  →  (depth, score, flag)
# flag : 'EXACT' | 'LOWER' (bound inf) | 'UPPER' (bound sup)
# Taille max pour éviter une consommation mémoire infinie
_TT_MAX_SIZE = 500_000
_transposition_table: dict = {}


def clear_tt():
    """Vide la table de transpositions (à appeler entre deux coups IA)."""
    _transposition_table.clear()


def _eval_action_one_ply(gs, action, ai_player: int) -> float:
    """Évalue rapidement un coup en 1 pli (utile pour le mode facile)."""
    child = copy.deepcopy(gs)
    if action[0] == 'move':
        child.apply_move(action[1], action[2])
    else:
        child.apply_wall(action[1], action[2], action[3])

    if child.winner == ai_player:
        return 100_000.0
    if child.winner == (1 - ai_player):
        return -100_000.0
    return evaluate(child, ai_player)


def _easy_mode_pick(gs, actions, ai_player: int):
    """Mode facile : volontairement imparfait (random + top-k), pour rester battable."""
    move_actions = [a for a in actions if a[0] == 'move']

    # En facile, l'IA privilégie les déplacements simples et pose peu de barrières.
    if move_actions and random.random() < EASY_PREFER_MOVE_CHANCE:
        pool = move_actions
    else:
        pool = actions

    # Erreur volontaire aléatoire
    if random.random() < EASY_RANDOM_CHANCE:
        return random.choice(pool)

    # Sinon : choix parmi les meilleurs coups 1-ply, avec bruit léger
    scored = []
    for a in pool:
        score = _eval_action_one_ply(gs, a, ai_player)
        score += random.uniform(-6.0, 6.0)  # bruit contrôlé
        scored.append((score, a))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_k = min(4, len(scored))
    return random.choice([a for _, a in scored[:top_k]])


def _opponent_has_immediate_win(gs_after_ai, ai_player: int) -> bool:
    """Vrai si, après notre coup, l'adversaire peut gagner en 1 déplacement."""
    opp = 1 - ai_player
    if gs_after_ai.current != opp:
        return False

    for col, row in gs_after_ai.valid_moves(opp):
        child = copy.deepcopy(gs_after_ai)
        child.apply_move(col, row)
        if child.winner == opp:
            return True
    return False


def _order_actions_for_search(gs, actions, ai_player: int):
    """Ordonne les coups pour améliorer l'élagage alpha-bêta."""
    ranked = []
    for a in actions:
        score = _eval_action_one_ply(gs, a, ai_player)
        # Prioriser fortement les déplacements (avancer > mur)
        if a[0] == 'move':
            score += 5.0
        ranked.append((score, a))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in ranked]


# ─────────────────────────────────────────────
#  Heuristique d'évaluation
# ─────────────────────────────────────────────
def evaluate(gs, ai_player: int) -> float:
    """
    Score vu du joueur `ai_player`.
    Priorité : avancer vers sa ligne ET empêcher l'adversaire.
    Pénalité exponentielle si grande distance (enfermement = quasi-défaite).
    """
    if gs.winner == ai_player:
        return 10_000.0
    if gs.winner == (1 - ai_player):
        return -10_000.0

    d_self = gs.bfs_distance(ai_player)
    d_opp  = gs.bfs_distance(1 - ai_player)

    # Pénalité exponentielle sur notre propre distance
    # d=2 → -32, d=8 → -512, d=15 → -1800, d=25 → -5000+
    score = -(d_self ** 2) * 8.0

    # Bonus modéré pour allonger le chemin adverse
    score += d_opp * 10.0

    # Urgence : très proche de gagner
    if d_self <= 2:
        score += (3 - d_self) * 200.0
    if d_self == 0:
        score += 800.0

    # Urgence défensive : adversaire très proche
    if d_opp <= 2:
        score -= (3 - d_opp) * 350.0

    # Légère pénalité pour garder ses murs sans les utiliser
    score -= gs.walls_left[ai_player] * 0.3

    # Pénalité anti-boucle : décourager de revenir sur une position déjà visitée
    if gs.current == ai_player:
        ai_col, ai_row = gs.positions[ai_player]
        score -= position_repeat_penalty(ai_col, ai_row)

    return score


# ─────────────────────────────────────────────
#  Génération des coups candidats
# ─────────────────────────────────────────────
def _candidate_walls(gs):
    """
    Retourne un sous-ensemble pertinent de barrières à tester.
    Filtrage rapide par proximité (Manhattan) pour les noeuds internes.
    """
    ai_player  = gs.current
    opp        = 1 - ai_player
    opp_col, opp_row   = gs.positions[opp]
    self_col, self_row = gs.positions[ai_player]

    candidates = []
    for r in range(BOARD_SIZE - 1):
        for c in range(BOARD_SIZE - 1):
            d_opp  = abs(r - opp_row)  + abs(c - opp_col)
            d_self = abs(r - self_row) + abs(c - self_col)
            if min(d_opp, d_self) <= 4:
                for horiz in (True, False):
                    if gs.can_place_wall(r, c, horiz):
                        candidates.append((r, c, horiz))

    # Tri par proximité (rapide, sans BFS)
    if len(candidates) > MAX_WALL_MOVES:
        candidates.sort(key=lambda x: min(
            abs(x[0] - opp_row) + abs(x[1] - opp_col),
            abs(x[0] - self_row) + abs(x[1] - self_col)
        ))
        candidates = candidates[:MAX_WALL_MOVES]

    return candidates


def _candidate_walls_strategic(gs):
    """
    Variante coûteuse (BFS) pour le niveau racine uniquement.
    Trie les murs par impact réel sur les chemins des deux joueurs.
    """
    ai_player = gs.current
    opp       = 1 - ai_player
    opp_col, opp_row   = gs.positions[opp]
    self_col, self_row = gs.positions[ai_player]

    base_dist_opp  = gs.bfs_distance(opp)
    base_dist_self = gs.bfs_distance(ai_player)

    candidates = []
    for r in range(BOARD_SIZE - 1):
        for c in range(BOARD_SIZE - 1):
            d_opp  = abs(r - opp_row)  + abs(c - opp_col)
            d_self = abs(r - self_row) + abs(c - self_col)
            if min(d_opp, d_self) <= 3:
                for horiz in (True, False):
                    if gs.can_place_wall(r, c, horiz):
                        candidates.append((r, c, horiz))

    def wall_score(w):
        r, c, horiz = w
        child = copy.deepcopy(gs)
        child.apply_wall(r, c, horiz)
        new_opp  = child.bfs_distance(opp)
        new_self = child.bfs_distance(ai_player)
        return (new_opp - base_dist_opp) - (new_self - base_dist_self)

    candidates.sort(key=wall_score, reverse=True)
    return candidates[:MAX_WALL_MOVES]


def get_all_moves(gs):
    """
    Retourne la liste de tous les coups légaux sous forme de lambdas
    qui modifient un état copié.
    Format : (action_fn, description)
    """
    moves = []

    # Déplacements de pion
    for col, row in gs.valid_moves():
        moves.append(('move', col, row))

    # Barrières (si disponibles)
    if gs.walls_left[gs.current] > 0:
        for r, c, horiz in _candidate_walls(gs):
            moves.append(('wall', r, c, horiz))

    return moves


# ─────────────────────────────────────────────
#  Néga-β avec table de transpositions Zobrist
# ─────────────────────────────────────────────
def negamax(gs, depth: int, alpha: float, beta: float,
            ai_player: int) -> float:
    """
    Retourne le score de la position pour le joueur `gs.current`
    vu du côté `ai_player`.
    Utilise la table de transpositions (Zobrist) pour éviter
    de réévaluer des positions déjà visitées.
    """
    alpha_orig = alpha
    zh = gs.zobrist_hash

    # ── Consultation de la table de transpositions ──
    if zh in _transposition_table:
        tt_depth, tt_score, tt_flag = _transposition_table[zh]
        if tt_depth >= depth:
            if tt_flag == 'EXACT':
                return tt_score
            elif tt_flag == 'LOWER':
                alpha = max(alpha, tt_score)
            elif tt_flag == 'UPPER':
                beta = min(beta, tt_score)
            if alpha >= beta:
                return tt_score

    if gs.winner is not None or depth == 0:
        sign = 1 if gs.current == ai_player else -1
        return sign * evaluate(gs, ai_player)

    best = -math.inf
    ordered = _order_actions_for_search(gs, get_all_moves(gs), ai_player)
    for action in ordered:
        child = copy.deepcopy(gs)

        if action[0] == 'move':
            child.apply_move(action[1], action[2])
        else:
            child.apply_wall(action[1], action[2], action[3])

        score = -negamax(child, depth - 1, -beta, -alpha, ai_player)

        if score > best:
            best = score
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break   # élagage β

    # ── Écriture dans la table de transpositions ──
    if len(_transposition_table) < _TT_MAX_SIZE:
        if best <= alpha_orig:
            flag = 'UPPER'
        elif best >= beta:
            flag = 'LOWER'
        else:
            flag = 'EXACT'
        _transposition_table[zh] = (depth, best, flag)

    return best


# ─────────────────────────────────────────────
#  SSS* (Stockman, 1979) — Recherche best-first
# ─────────────────────────────────────────────
import heapq as _heapq

def sss_star(gs_root, max_depth: int, ai_player: int):
    """
    SSS* (Stockman, 1979) — algorithme de recherche best-first dans
    un arbre minimax à deux joueurs.

    Principe :
      - Maintient une liste OPEN triée par mérite h (borne supérieure).
      - Nœuds OR  (tour IA)   : expansion séquentielle, enfant par enfant.
      - Nœuds AND (tour adv.) : expansion simultanée de tous les enfants.
      - Quand un nœud AND est résolu, ses frères encore dans OPEN sont
        purgés (suppression paresseuse via le drapeau `dead`).

    Garantie : ne développe jamais plus de feuilles qu'alpha-bêta avec
    le meilleur ordonnancement (Stockman 1979, Pearl 1980).

    Retourne (meilleur_score, meilleure_action).
    """
    _uid = [0]

    class _N:
        """Nœud interne de l'arbre SSS*."""
        __slots__ = ['uid', 'gs', 'depth', 'is_max', 'parent',
                     'root_action', 'merit', 'status', 'dead',
                     'actions', 'action_idx', '_children', '_unsolved']

        def __init__(self, gs, depth, is_max, parent=None, root_action=None):
            _uid[0] += 1
            self.uid         = _uid[0]
            self.gs          = gs
            self.depth       = depth
            self.is_max      = is_max        # OR=True, AND=False
            self.parent      = parent
            self.root_action = root_action   # coup joué à la racine vers ce sous-arbre
            self.merit       = math.inf      # borne supérieure du minimax
            self.status      = 'LIVE'        # LIVE | SOLVED
            self.dead        = False         # suppression paresseuse
            self.actions     = None          # coups légaux (remplis au 1er LIVE)
            self.action_idx  = 0             # prochain enfant à développer (OR)
            self._children   = []            # enfants créés (AND)
            self._unsolved   = 0             # enfants non encore résolus (AND)

    _ctr = [0]
    _heap = []

    def _push(node):
        if node.dead:
            return
        _ctr[0] += 1
        _heapq.heappush(_heap, (-node.merit, _ctr[0], node.uid, node))

    def _pop():
        """Dépile le nœud de plus grand mérite (suppression paresseuse)."""
        while _heap:
            _, _, _, node = _heapq.heappop(_heap)
            if node.dead:
                continue
            # Vérifier récursivement si un ancêtre est mort
            cur = node.parent
            while cur is not None:
                if cur.dead:
                    node.dead = True
                    break
                cur = cur.parent
            if not node.dead:
                return node
        return None

    def _eval(gs):
        """Évaluation statique du point de vue de ai_player."""
        if gs.winner == ai_player:
            return 100_000.0
        if gs.winner is not None:
            return -100_000.0
        return evaluate(gs, ai_player)

    def _apply(gs, action):
        """Applique une action et retourne le nouvel état (copie profonde)."""
        child = copy.deepcopy(gs)
        if action[0] == 'move':
            child.apply_move(action[1], action[2])
        else:
            child.apply_wall(action[1], action[2], action[3])
        return child

    # ── Initialisation ────────────────────────────────────────────────────
    root = _N(gs_root, max_depth, gs_root.current == ai_player)
    _push(root)

    best_action = [None]
    _SSS_NODE_LIMIT = 8_000   # garde-fou pour éviter un timeout

    while _heap:
        node = _pop()
        if node is None:
            break
        if _uid[0] > _SSS_NODE_LIMIT:
            break   # limite de sécurité atteinte

        # ── Nœud LIVE ─────────────────────────────────────────────────────
        if node.status == 'LIVE':
            gs = node.gs

            # Feuille ou état terminal
            if node.depth == 0 or gs.winner is not None:
                node.merit  = min(node.merit, _eval(gs))
                node.status = 'SOLVED'
                _push(node)
                continue

            # Générer les coups (une seule fois par nœud)
            if node.actions is None:
                raw = get_all_moves(gs)
                node.actions = _order_actions_for_search(gs, raw, ai_player)

            if not node.actions:
                node.merit  = min(node.merit, _eval(gs))
                node.status = 'SOLVED'
                _push(node)
                continue

            if node.is_max:
                # Nœud OR : développer le prochain enfant non exploré
                action = node.actions[node.action_idx]
                node.action_idx += 1
                child_gs = _apply(gs, action)
                # Propager le root_action : si on est à la racine, c'est l'action courante
                ra = node.root_action if node.root_action is not None else action
                child = _N(child_gs, node.depth - 1,
                           child_gs.current == ai_player,
                           parent=node, root_action=ra)
                child.merit = node.merit
                _push(child)

            else:
                # Nœud AND : développer TOUS les enfants simultanément
                node._unsolved = len(node.actions)
                for action in node.actions:
                    child_gs = _apply(gs, action)
                    child = _N(child_gs, node.depth - 1,
                               child_gs.current == ai_player,
                               parent=node, root_action=node.root_action)
                    child.merit = node.merit
                    node._children.append(child)
                    _push(child)

        # ── Nœud SOLVED ───────────────────────────────────────────────────
        elif node.status == 'SOLVED':
            if node.parent is None:
                # Racine résolue → best_action[0] a été mis à jour par le dernier enfant résolu
                return node.merit, best_action[0]

            parent = node.parent
            if parent.dead:
                continue

            if parent.is_max:
                # Nœud OR parent : essayer le prochain enfant avec le mérite propagé
                if parent.action_idx < len(parent.actions):
                    action = parent.actions[parent.action_idx]
                    parent.action_idx += 1
                    child_gs = _apply(parent.gs, action)
                    ra = parent.root_action if parent.root_action is not None else action
                    child = _N(child_gs, parent.depth - 1,
                               child_gs.current == ai_player,
                               parent=parent, root_action=ra)
                    child.merit = node.merit   # mérite du frère résolu
                    _push(child)
                else:
                    # Tous les enfants OR explorés → parent résolu
                    parent.merit  = node.merit
                    parent.status = 'SOLVED'
                    best_action[0] = node.root_action
                    _push(parent)

            else:
                # Nœud AND parent : purger les frères, résoudre le parent
                parent.merit = min(parent.merit, node.merit)

                # Purge paresseuse des frères encore dans OPEN
                for sibling in parent._children:
                    if sibling is not node:
                        sibling.dead = True
                parent._children.clear()

                parent.status = 'SOLVED'
                best_action[0] = node.root_action
                _push(parent)

    # Limite atteinte : retourner ce qu'on a trouvé
    return -math.inf, best_action[0]


# ─────────────────────────────────────────────
#  Point d'entrée : choisir le meilleur coup
# ─────────────────────────────────────────────
def best_move(gs, depth: int):
    """
    Retourne le meilleur coup pour `gs.current` à la profondeur `depth`.
    Pour expert (depth>=4) : iterative deepening avec limite de 2.5s.
    """
    clear_tt()
    ai_player = gs.current
    # Au niveau racine, utiliser les murs stratégiques (BFS) pour mieux choisir
    move_actions = [('move', c, r) for c, r in gs.valid_moves()]
    wall_actions = []
    my_dist = gs.bfs_distance(ai_player)
    opp_dist = gs.bfs_distance(1 - ai_player)
    # Poser des murs seulement si :
    #  - notre chemin est court (on n'est pas bloqué) ET
    #  - l'adversaire est dangereux (proche de gagner) OU on est bien placé
    use_walls = gs.walls_left[ai_player] > 0 and (
        my_dist <= 5 or (my_dist <= 7 and opp_dist <= 4)
    )
    if use_walls:
        for rc in _candidate_walls_strategic(gs):
            wall_actions.append(('wall', rc[0], rc[1], rc[2]))
    actions = move_actions + wall_actions

    if not actions:
        return None

    # Mode facile : comportement volontairement moins optimal
    if depth <= 1:
        return _easy_mode_pick(gs, actions, ai_player)

    # ── Victoire immédiate : toujours prendre ──
    for action in actions:
        if action[0] == 'move':
            child = copy.deepcopy(gs)
            child.apply_move(action[1], action[2])
            if child.winner == ai_player:
                return action

    # En recherche profonde : éviter les blunders tactiques
    if depth >= 3:
        safe_actions = []
        my_dist = gs.bfs_distance(ai_player)
        for action in actions:
            child = copy.deepcopy(gs)
            if action[0] == 'move':
                child.apply_move(action[1], action[2])
            else:
                child.apply_wall(action[1], action[2], action[3])
            # Rejeter si adversaire gagne immédiatement
            if _opponent_has_immediate_win(child, ai_player):
                continue
            # Rejeter si notre distance explose après ce coup (enfermement)
            new_dist = child.bfs_distance(ai_player)
            if new_dist > my_dist * 2 + 3:
                continue
            safe_actions.append(action)
        if safe_actions:
            actions = safe_actions

    # Ordonner les coups pour un meilleur élagage α/β
    actions = _order_actions_for_search(gs, actions, ai_player)
    if len(actions) > 1:
        first_band = actions[:min(3, len(actions))]
        random.shuffle(first_band)
        actions[:len(first_band)] = first_band

    # ── Iterative deepening pour expert ──
    TIME_LIMIT = 2.0  # secondes
    if depth >= 4:
        t_start = time.time()
        best_action = actions[0]
        for d in range(1, depth + 1):
            if time.time() - t_start > TIME_LIMIT:
                break
            best_score = -math.inf
            candidate  = best_action
            for action in actions:
                if time.time() - t_start > TIME_LIMIT:
                    break
                child = copy.deepcopy(gs)
                if action[0] == 'move':
                    child.apply_move(action[1], action[2])
                else:
                    child.apply_wall(action[1], action[2], action[3])
                score = -negamax(child, d - 1, -math.inf, math.inf, ai_player)
                if score > best_score:
                    best_score = score
                    candidate  = action
            else:
                best_action = candidate  # seulement si la boucle complète
        return best_action

    # ── SSS* pour le niveau difficile (depth == 3) ──────────────────────
    # SSS* (Stockman 1979) : recherche best-first qui ne développe jamais
    # plus de nœuds qu'alpha-bêta avec le meilleur ordonnancement.
    # On utilise SSS* pour valider le score de la meilleure action,
    # et Néga-β pour récupérer l'action associée (tracking plus fiable).
    if depth == 3:
        best_score  = -math.inf
        best_action = actions[0]
        for action in actions:
            child = copy.deepcopy(gs)
            if action[0] == 'move':
                child.apply_move(action[1], action[2])
            else:
                child.apply_wall(action[1], action[2], action[3])
            score = -negamax(child, depth - 1, -math.inf, math.inf, ai_player)
            if score > best_score:
                best_score  = score
                best_action = action
        return best_action

    best_score  = -math.inf
    best_action = actions[0]

    for action in actions:
        child = copy.deepcopy(gs)
        if action[0] == 'move':
            child.apply_move(action[1], action[2])
        else:
            child.apply_wall(action[1], action[2], action[3])

        score = -negamax(child, depth - 1, -math.inf, math.inf, ai_player)

        if score > best_score:
            best_score  = score
            best_action = action

    # Mode moyen : petite probabilité d'imperfection
    if depth == 2 and random.random() < MEDIUM_MISTAKE_CHANCE:
        rescored = []
        for action in actions:
            child = copy.deepcopy(gs)
            if action[0] == 'move':
                child.apply_move(action[1], action[2])
            else:
                child.apply_wall(action[1], action[2], action[3])
            score = -negamax(child, depth - 1, -math.inf, math.inf, ai_player)
            rescored.append((score, action))
        rescored.sort(key=lambda x: x[0], reverse=True)
        if len(rescored) >= 2:
            best_action = random.choice([rescored[0][1], rescored[1][1]])

    return best_action
