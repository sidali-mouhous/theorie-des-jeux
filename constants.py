# ─────────────────────────────────────────────
#  Quoridor — Constantes globales
# ─────────────────────────────────────────────

# Grille
BOARD_SIZE   = 9          # 9×9 cases
CELL_SIZE    = 68         # pixels par case
WALL_THICK   = 10         # épaisseur d'une barrière (px)
WALL_GAP     = 4          # espacement entre cases (px)
MARGIN       = 48         # marge autour du plateau

# Fenêtre
TILE = CELL_SIZE + WALL_GAP
BOARD_PX = BOARD_SIZE * TILE - WALL_GAP   # largeur/hauteur du plateau en px
WIN_W    = BOARD_PX + MARGIN * 2 + 260    # +panneau latéral
WIN_H    = BOARD_PX + MARGIN * 2

# ── Palette ───────────────────────────────────
BG          = (18,  18,  28)   # fond général
BOARD_BG    = (30,  30,  46)   # fond plateau
CELL_CLR    = (44,  46,  74)   # case normale
CELL_HOVER  = (60,  62,  98)   # case survolée
GRID_LINE   = (28,  28,  44)   # séparateur de grille
WALL_CLR    = (230, 190,  60)  # barrière posée
WALL_GHOST_OK  = (230, 190,  60, 130)  # fantôme valide
WALL_GHOST_BAD = (220,  60,  60, 110)  # fantôme invalide (rouge)

P1_CLR      = ( 70, 160, 240)  # joueur 1 — bleu
P2_CLR      = (240,  80,  80)  # joueur 2 — rouge
P1_DARK     = ( 30,  90, 160)
P2_DARK     = (160,  30,  30)
PAWN_OUTLINE= (220, 220, 220)

MOVE_HINT   = ( 55,  90,  55)   # case accessible (déplacement)
MOVE_HOVER  = ( 80, 140,  80)   # case accessible + survolée
MOVE_DOT    = (100, 200,  90)   # petit point indicateur
ACTIVE_CELL = ( 60,  80, 120)   # case du pion actif

PANEL_BG    = (24,  24,  38)
TEXT_CLR    = (210, 210, 230)
TEXT_DIM    = (100, 100, 130)
ACCENT      = (120, 200, 100)

# Polices (chargées dans main)
FONT_SM = 16
FONT_MD = 22
FONT_LG = 34

# Nombre de barrières par joueur
WALLS_PER_PLAYER = 10
