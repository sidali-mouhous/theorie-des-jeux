# ─────────────────────────────────────────────
#  Quoridor — Rendu visuel du plateau (V3)
# ─────────────────────────────────────────────
import math
import pygame
from constants import *


# ── Utilitaires ──────────────────────────────
def cell_rect(col: int, row: int) -> pygame.Rect:
    """Retourne le pygame.Rect d'une case (col, row) en coordonnées écran."""
    x = MARGIN + col * TILE
    y = MARGIN + row * TILE
    return pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)


def pixel_to_cell(mx: int, my: int):
    """Convertit des coordonnées souris en (col, row), ou None si hors plateau."""
    col = (mx - MARGIN) // TILE
    row = (my - MARGIN) // TILE
    if 0 <= col < BOARD_SIZE and 0 <= row < BOARD_SIZE:
        r = cell_rect(col, row)
        if r.collidepoint(mx, my):
            return col, row
    return None


# ── Plateau ───────────────────────────────────
def draw_board(surface: pygame.Surface,
               valid_moves: list = None,
               hovered: tuple = None,
               active_pos: tuple = None):
    """Dessine le fond, les 81 cases et les surlignages."""
    board_rect = pygame.Rect(
        MARGIN - WALL_GAP,
        MARGIN - WALL_GAP,
        BOARD_PX + WALL_GAP * 2,
        BOARD_PX + WALL_GAP * 2,
    )
    pygame.draw.rect(surface, BOARD_BG, board_rect, border_radius=12)

    valid_set   = set(valid_moves) if valid_moves else set()
    hovered_set = {hovered}        if hovered     else set()

    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            r   = cell_rect(col, row)
            pos = (col, row)

            if pos in valid_set and pos in hovered_set:
                clr = MOVE_HOVER
            elif pos in valid_set:
                clr = MOVE_HINT
            elif pos == active_pos:
                clr = ACTIVE_CELL
            elif pos in hovered_set:
                clr = CELL_HOVER
            else:
                clr = CELL_CLR if (row + col) % 2 == 0 else (40, 42, 68)

            pygame.draw.rect(surface, clr, r, border_radius=6)

            if pos in valid_set and pos not in hovered_set:
                pygame.draw.circle(surface, MOVE_DOT, r.center, 5)


def draw_move_direction_arrows(surface: pygame.Surface,
                               current_pos: tuple,
                               valid_moves: list,
                               color: tuple = None):
    """Dessine des flèches depuis le pion actif vers les cases de déplacement valides."""
    if not current_pos or not valid_moves:
        return

    col, row = current_pos
    src = cell_rect(col, row).center
    arrow_color = color if color is not None else MOVE_DOT

    for mc, mr in valid_moves:
        dst = cell_rect(mc, mr).center

        # Segment principal
        pygame.draw.line(surface, arrow_color, src, dst, 3)

        # Pointe de flèche orientée vers dst
        dx = dst[0] - src[0]
        dy = dst[1] - src[1]
        norm = (dx * dx + dy * dy) ** 0.5
        if norm < 1:
            continue
        ux, uy = dx / norm, dy / norm

        tip = (dst[0], dst[1])
        left = (dst[0] - ux * 12 - uy * 6,
                dst[1] - uy * 12 + ux * 6)
        right = (dst[0] - ux * 12 + uy * 6,
                 dst[1] - uy * 12 - ux * 6)

        pygame.draw.polygon(surface, arrow_color, [tip, left, right])


# ── Coordonnées ──────────────────────────────
def draw_coordinates(surface: pygame.Surface, font: pygame.font.Font):
    letters = "ABCDEFGHI"
    for i in range(BOARD_SIZE):
        cx     = cell_rect(i, 0).centerx
        cy_top = MARGIN - 26
        cy_bot = MARGIN + BOARD_PX + 10
        lbl    = font.render(letters[i], True, TEXT_DIM)
        surface.blit(lbl, lbl.get_rect(centerx=cx, centery=cy_top))
        surface.blit(lbl, lbl.get_rect(centerx=cx, centery=cy_bot))

        rx_l = MARGIN - 26
        ry   = cell_rect(0, i).centery
        num  = font.render(str(BOARD_SIZE - i), True, TEXT_DIM)
        surface.blit(num, num.get_rect(centerx=rx_l, centery=ry))
        rx_r = MARGIN + BOARD_PX + 12
        surface.blit(num, num.get_rect(centerx=rx_r, centery=ry))


# ── Pion ──────────────────────────────────────
def draw_pawn(surface: pygame.Surface, col: int, row: int,
              color: tuple, dark: tuple, label: str,
              font: pygame.font.Font, active: bool = False,
              pixel_pos: tuple = None):
    """
    Dessine un pion avec ombre, dégradé et halo si actif.
    `pixel_pos` : (cx, cy) en pixels pour l'animation — remplace la position de case.
    """
    if pixel_pos:
        cx, cy = pixel_pos
    else:
        r      = cell_rect(col, row)
        cx, cy = r.centerx, r.centery
    radius = CELL_SIZE // 2 - 6

    if active:
        halo = pygame.Surface((radius * 2 + 20, radius * 2 + 20), pygame.SRCALPHA)
        pygame.draw.circle(halo, (*color[:3], 55),
                           (radius + 10, radius + 10), radius + 8)
        surface.blit(halo, (cx - radius - 10, cy - radius - 10))

    shadow = pygame.Surface((radius * 2 + 12, radius * 2 + 12), pygame.SRCALPHA)
    pygame.draw.circle(shadow, (0, 0, 0, 90),
                       (radius + 6, radius + 8), radius)
    surface.blit(shadow, (cx - radius - 6, cy - radius - 4))

    pygame.draw.circle(surface, dark,  (cx, cy + 2), radius)
    pygame.draw.circle(surface, color, (cx, cy),     radius)

    lighter = tuple(min(c + 60, 255) for c in color[:3])
    pygame.draw.circle(surface, lighter, (cx - 5, cy - 5), radius // 3)
    pygame.draw.circle(surface, (220, 220, 220), (cx, cy), radius, 2)

    lbl = font.render(label, True, (255, 255, 255))
    surface.blit(lbl, lbl.get_rect(center=(cx, cy)))


# ── Surbrillance du coup IA en attente ────────
def draw_ai_preview(surface: pygame.Surface, action, horizontal: bool = True):
    """
    Affiche le coup que l'IA s'apprête à jouer (avant le délai).
    action : ('move', col, row) ou ('wall', r, c, horiz)
    """
    if action is None:
        return
    if action[0] == 'move':
        col, row = action[1], action[2]
        r = cell_rect(col, row)
        hl = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        hl.fill((255, 200, 0, 80))
        pygame.draw.rect(hl, (255, 200, 0, 180), hl.get_rect(), 3, border_radius=6)
        surface.blit(hl, r.topleft)
    else:
        from renderer import _wall_rect   # import local pour éviter la circularité
        rr, c, horiz = action[1], action[2], action[3]
        rect = _wall_rect(rr, c, horiz)
        ov = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        ov.fill((255, 200, 0, 160))
        surface.blit(ov, rect.topleft)


# ── Panneau latéral ───────────────────────────
def draw_panel(surface: pygame.Surface, fonts: dict, state: dict):
    now   = pygame.time.get_ticks()
    px    = MARGIN + BOARD_PX + WALL_GAP + 20
    panel = pygame.Rect(px, MARGIN - WALL_GAP, 236, BOARD_PX + WALL_GAP * 2)

    # Fond avec liseret supérieur animé
    pygame.draw.rect(surface, PANEL_BG, panel, border_radius=12)
    pulse_a = int(110 + 70 * math.sin(now / 900))
    top_glow = pygame.Surface((panel.w - 4, 3), pygame.SRCALPHA)
    top_glow.fill((*ACCENT[:3], pulse_a))
    surface.blit(top_glow, (panel.x + 2, panel.y + 2))

    CX   = panel.centerx
    PADL = px + 12
    PADR = px + 224
    W    = PADR - PADL

    def sep_line(y):
        sl = pygame.Surface((W, 1), pygame.SRCALPHA)
        sl.fill((40, 42, 64, 100))
        surface.blit(sl, (PADL, y))

    # ═══ 1. TITRE ANIMÉ ══════════════════════════════════
    y = panel.top + 14
    pulse = 0.80 + 0.20 * math.sin(now / 800)
    tc_col = (int(ACCENT[0] * pulse), int(ACCENT[1] * pulse), int(ACCENT[2] * pulse))
    t = fonts['lg'].render("QUORIDOR", True, tc_col)
    surface.blit(t, t.get_rect(centerx=CX, top=y))
    y += t.get_height() + 3
    sub = fonts['sm'].render("Univ. Rouen  ·  M1 GIL-ITA", True, TEXT_DIM)
    surface.blit(sub, sub.get_rect(centerx=CX, top=y))
    y += sub.get_height() + 14

    sep_line(y); y += 10

    # ═══ 2. SCORE SESSION ════════════════════════════════
    scores = state.get('scores', [0, 0])
    s1 = fonts['lg'].render(str(scores[0]), True, P1_CLR)
    vs = fonts['sm'].render("vs", True, TEXT_DIM)
    s2 = fonts['lg'].render(str(scores[1]), True, P2_CLR)
    j1 = fonts['sm'].render("J1", True, P1_CLR)
    j2 = fonts['sm'].render("J2", True, P2_CLR)
    surface.blit(s1, s1.get_rect(right=CX - 14, centery=y + 18))
    surface.blit(vs, vs.get_rect(centerx=CX,     centery=y + 18))
    surface.blit(s2, s2.get_rect(left=CX  + 14, centery=y + 18))
    surface.blit(j1, j1.get_rect(right=CX - 14, top=y + 36))
    surface.blit(j2, j2.get_rect(left=CX  + 14, top=y + 36))
    y += 56

    sep_line(y); y += 12

    # ═══ 3. TOUR — indicateur circulaire animé ═══════════
    turn     = state.get('turn', 1)
    tc       = state.get('turn_count', 0)
    clr_turn = P1_CLR if turn == 1 else P2_CLR
    dark_t   = P1_DARK if turn == 1 else P2_DARK

    pulse2    = 0.55 + 0.45 * math.sin(now / 500)
    ccx       = PADL + 22
    ccy       = y + 22
    halo_s    = pygame.Surface((56, 56), pygame.SRCALPHA)
    pygame.draw.circle(halo_s, (*clr_turn[:3], int(55 * pulse2)), (28, 28), 26)
    surface.blit(halo_s, (ccx - 28, ccy - 28))
    pygame.draw.circle(surface, dark_t,       (ccx, ccy + 2), 19)
    pygame.draw.circle(surface, clr_turn,     (ccx, ccy),     17)
    pygame.draw.circle(surface, (255,255,255),(ccx, ccy),     17, 1)
    ln = fonts['sm'].render(str(turn), True, (255, 255, 255))
    surface.blit(ln, ln.get_rect(center=(ccx, ccy)))

    t1 = fonts['md'].render(f"Tour {tc + 1}", True, TEXT_CLR)
    t2 = fonts['sm'].render(f"Joueur {turn}", True, clr_turn)
    surface.blit(t1, (PADL + 50, y + 6))
    surface.blit(t2, (PADL + 50, y + 6 + t1.get_height() + 2))
    y += 52

    sep_line(y); y += 10

    # ═══ 4. FICHES JOUEURS ════════════════════════════════
    dist = state.get('dist', [0, 0])
    for i, (clr, dark) in enumerate([(P1_CLR, P1_DARK), (P2_CLR, P2_DARK)]):
        is_active = (turn == i + 1)
        card = pygame.Rect(PADL, y, W, 102)

        # Fond et bordure de la carte
        pygame.draw.rect(surface,
                         (36, 38, 62) if is_active else (26, 28, 46),
                         card, border_radius=10)
        pygame.draw.rect(surface,
                         clr if is_active else (34, 36, 56),
                         card, 2 if is_active else 1, border_radius=10)

        # Pion
        pc = (card.left + 22, card.top + 24)
        pygame.draw.circle(surface, dark,         (pc[0], pc[1] + 2), 16)
        pygame.draw.circle(surface, clr,           pc,                 14)
        lighter = tuple(min(c + 70, 255) for c in clr[:3])
        pygame.draw.circle(surface, lighter,      (pc[0]-4, pc[1]-4),  5)
        pygame.draw.circle(surface, (220,220,220), pc,                 14, 1)
        lp = fonts['sm'].render(f"J{i+1}", True, (255, 255, 255))
        surface.blit(lp, lp.get_rect(center=pc))

        # Nom du joueur
        nm = fonts['md'].render(f"Joueur {i+1}",
                                True, clr if is_active else TEXT_CLR)
        surface.blit(nm, (card.left + 46, card.top + 6))

        # Icônes barrières
        w = state['walls'][i]
        wl = fonts['sm'].render(f"{w}/10",
                                True, TEXT_CLR if is_active else TEXT_DIM)
        surface.blit(wl, (card.left + 46, card.top + 30))
        for wi in range(WALLS_PER_PLAYER):
            ic = WALL_CLR if wi < w else (30, 32, 52)
            pygame.draw.rect(surface, ic,
                             pygame.Rect(card.left + 46 + wi * 14,
                                         card.top + 50, 10, 10),
                             border_radius=2)

        # Barre de progression vers la victoire
        d   = dist[i]
        prg = max(0.0, 1.0 - d / 16.0)
        bx  = card.left + 10
        by  = card.top + 76
        bw  = W - 20
        pygame.draw.rect(surface, (20, 22, 42),
                         pygame.Rect(bx, by, bw, 8), border_radius=4)
        fw = max(4, int(bw * prg))
        bar_c = clr if is_active else tuple(c // 2 + 10 for c in clr[:3])
        pygame.draw.rect(surface, bar_c,
                         pygame.Rect(bx, by, fw, 8), border_radius=4)
        dl = fonts['sm'].render(f"{d} cases", True, TEXT_DIM)
        surface.blit(dl, dl.get_rect(right=card.right - 6, centery=by + 4))

        y += card.h + 8

    y += 4
    sep_line(y); y += 10

    # ═══ 5. STATUT / IA ═══════════════════════════════════
    status = state.get('status', '')
    ai_lbl = state.get('ai_label', '')
    if status:
        s = fonts['sm'].render(status, True, ACCENT)
        surface.blit(s, s.get_rect(centerx=CX, top=y))
        y += s.get_height() + 4
    if ai_lbl:
        a = fonts['sm'].render(ai_lbl, True, TEXT_DIM)
        surface.blit(a, a.get_rect(centerx=CX, top=y))

    # ═══ 6. RACCOURCIS (bas) ══════════════════════════════
    HINTS_H = 5 * 20 + 14
    sep_line(panel.bottom - HINTS_H - 6)
    hints = [("B",   "Barrière"),
             ("H",   "Rotation"),
             ("R",   "Rejouer"),
             ("ESC", "Menu"),
             ("?",   "Règles")]
    y = panel.bottom - HINTS_H
    for key, desc in hints:
        k = fonts['sm'].render(f"[{key}]", True, ACCENT)
        d = fonts['sm'].render(desc, True, TEXT_DIM)
        surface.blit(k, (PADL, y))
        surface.blit(d, (PADL + 52, y))
        y += 20



# ── Bandeau de victoire ───────────────────────
def draw_winner_banner(surface: pygame.Surface, fonts: dict, winner: int):
    color  = P1_CLR if winner == 0 else P2_CLR
    now    = pygame.time.get_ticks()
    pulse  = 0.75 + 0.25 * math.sin(now / 400)
    gold   = (int(220 * pulse), int(185 * pulse), int(40 * pulse))

    overlay = pygame.Surface((BOARD_PX + 20, 110), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    ox = MARGIN - 10
    oy = MARGIN + BOARD_PX // 2 - 55
    surface.blit(overlay, (ox, oy))

    banner_rect = pygame.Rect(ox, oy, BOARD_PX + 20, 110)
    pygame.draw.rect(surface, gold,  banner_rect, 2, border_radius=8)
    pygame.draw.rect(surface, color, banner_rect.inflate(-6, -6), 1, border_radius=6)

    cx   = ox + (BOARD_PX + 20) // 2
    msg  = fonts['lg'].render(f"Joueur {winner + 1} a gagne !", True, gold)
    sub  = fonts['md'].render("Félicitations !", True, color)
    hint = fonts['sm'].render("R  rejouer  ·  ESC  menu", True, TEXT_DIM)
    surface.blit(msg,  msg.get_rect(centerx=cx, top=oy + 8))
    surface.blit(sub,  sub.get_rect(centerx=cx, top=oy + 54))
    surface.blit(hint, hint.get_rect(centerx=cx, top=oy + 88))


# ── Calcul de la position d'une barrière ──────
def _wall_rect(r: int, c: int, horizontal: bool) -> pygame.Rect:
    """
    Retourne le Rect d'une barrière (2 segments).
    Barrière horizontale en (r,c) : entre row r et r+1, colonnes c et c+1.
    Barrière verticale   en (r,c) : entre col c et c+1, rangées r et r+1.
    """
    if horizontal:
        x = MARGIN + c * TILE
        y = MARGIN + (r + 1) * TILE - WALL_GAP - WALL_THICK // 2
        w = CELL_SIZE * 2 + WALL_GAP
        h = WALL_THICK
    else:
        x = MARGIN + (c + 1) * TILE - WALL_GAP - WALL_THICK // 2
        y = MARGIN + r * TILE
        w = WALL_THICK
        h = CELL_SIZE * 2 + WALL_GAP
    return pygame.Rect(x, y, w, h)


def wall_from_pixel(mx: int, my: int, horizontal: bool):
    """
    Détecte en quelle case-barrière (r, c) se trouve le curseur.
    Retourne (r, c) ou None.
    On cherche la barrière la plus proche du curseur.
    """
    best     = None
    best_dist = 18   # tolérance en pixels

    for r in range(BOARD_SIZE - 1):
        for c in range(BOARD_SIZE - 1):
            rect = _wall_rect(r, c, horizontal)
            cx   = rect.centerx
            cy   = rect.centery
            dist = abs(mx - cx) + abs(my - cy)
            if rect.inflate(12, 12).collidepoint(mx, my) and dist < best_dist:
                best_dist = dist
                best      = (r, c)
    return best


# ── Dessin des barrières posées ───────────────
def draw_walls(surface: pygame.Surface, h_walls, v_walls):
    """Dessine toutes les barrières déjà posées sur le plateau."""
    for r in range(BOARD_SIZE - 1):
        for c in range(BOARD_SIZE - 1):
            if h_walls[r][c]:
                rect = _wall_rect(r, c, horizontal=True)
                pygame.draw.rect(surface, WALL_CLR, rect, border_radius=4)
            if v_walls[r][c]:
                rect = _wall_rect(r, c, horizontal=False)
                pygame.draw.rect(surface, WALL_CLR, rect, border_radius=4)


# ── Aperçu fantôme d'une barrière ─────────────
def draw_wall_ghost(surface: pygame.Surface,
                    r: int, c: int, horizontal: bool,
                    valid: bool):
    """Aperçu semi-transparent de la barrière sous la souris."""
    rect  = _wall_rect(r, c, horizontal)
    color = WALL_GHOST_OK if valid else WALL_GHOST_BAD
    ghost = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    ghost.fill(color)
    pygame.draw.rect(ghost, (*color[:3], 200), ghost.get_rect(), border_radius=4)
    surface.blit(ghost, rect.topleft)


# ── Indicateur de mode (coin bas-gauche) ──────
def draw_mode_badge(surface: pygame.Surface, font: pygame.font.Font,
                    wall_mode: bool, horizontal: bool, walls_left: int):
    """Badge bas-plateau : indique le mode en cours."""
    if wall_mode:
        ori   = "Horizontale" if horizontal else "Verticale"
        txt   = f"● BARRIÈRE {ori}   [H] pivoter   [B] annuler"
        color = WALL_CLR
    elif walls_left > 0:
        txt   = "● DÉPLACEMENT   [B] → mode barrière"
        color = MOVE_HINT
    else:
        txt   = "● DÉPLACEMENT   (plus de barrières)"
        color = TEXT_DIM

    lbl = font.render(txt, True, color)
    bg  = pygame.Rect(MARGIN, MARGIN + BOARD_PX + WALL_GAP + 6,
                      lbl.get_width() + 16, lbl.get_height() + 8)
    pygame.draw.rect(surface, (20, 20, 32), bg, border_radius=6)
    pygame.draw.rect(surface, color,        bg, 1, border_radius=6)
    surface.blit(lbl, (bg.x + 8, bg.y + 4))


# ── Écran des règles ──────────────────────────
RULES = [
    ("Objectif",
     "Etre le 1er a atteindre la rangee opposee."),
    ("Deplacements",
     "Avancer d'une case (haut/bas/gauche/droite)."),
    ("Saut",
     "Si l'adversaire est adjacent, sauter par-dessus.\n"
     "Saut diagonal si le saut direct est bloque."),
    ("Barrieres",
     "Chaque joueur a 10 barrieres (2 cases).\n"
     "Une barriere ne peut pas bloquer totalement\n"
     "le chemin d'un joueur."),
    ("Victoire",
     "Atteindre n'importe quelle case de la ligne\n"
     "opposee. J1 (bleu) vise la rangee 1,\n"
     "J2 (rouge) vise la rangee 9."),
]


def draw_rules_screen(surface: pygame.Surface, fonts: dict):
    """
    Affiche l'écran des règles par-dessus tout.
    Retourne quand l'utilisateur appuie sur une touche ou clique.
    """
    W, H = surface.get_size()
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 210))
    surface.blit(overlay, (0, 0))

    panel_w, panel_h = 620, 520
    px = (W - panel_w) // 2
    py = (H - panel_h) // 2
    panel = pygame.Rect(px, py, panel_w, panel_h)
    pygame.draw.rect(surface, PANEL_BG, panel, border_radius=14)
    pygame.draw.rect(surface, ACCENT,   panel, 2, border_radius=14)

    y = py + 20
    title = fonts['lg'].render("Règles du Quoridor", True, ACCENT)
    surface.blit(title, title.get_rect(centerx=panel.centerx, top=y))
    y += title.get_height() + 16

    for section, text in RULES:
        # Titre de section
        stitle = fonts['md'].render(section, True, TEXT_CLR)
        surface.blit(stitle, (px + 24, y))
        y += stitle.get_height() + 4

        # Corps (multilignes)
        for line in text.split("\n"):
            lbl = fonts['sm'].render(line, True, TEXT_DIM)
            surface.blit(lbl, (px + 36, y))
            y += lbl.get_height() + 2
        y += 10

    # Bas
    hint = fonts['sm'].render("[ ? ] ou  [ Entrée ]  pour fermer", True, TEXT_DIM)
    surface.blit(hint, hint.get_rect(centerx=panel.centerx,
                                      bottom=py + panel_h - 14))

    pygame.display.flip()

    # Attendre interaction
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                import sys; sys.exit()
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return
        clock.tick(30)
