# ─────────────────────────────────────────────
#  Quoridor — Point d'entrée V6
#  Délai IA visible, animation pion, règles,
#  score session, interface complète
# ─────────────────────────────────────────────
import sys
import threading
import math
import pygame
from constants import *
from renderer import (draw_board, draw_coordinates, draw_pawn,
                      draw_panel, draw_winner_banner, pixel_to_cell,
                      draw_walls, draw_wall_ghost, draw_mode_badge,
                      draw_move_direction_arrows,
                      wall_from_pixel,
                      draw_rules_screen, cell_rect)
from game   import GameState
from ai     import best_move, LEVELS, reset_history, record_position
from sounds import Sounds

# Délai (ms) pendant lequel le coup IA est affiché avant d'être joué
AI_SHOW_DELAY = 600
# Durée (ms) de l'animation de glissement du pion
ANIM_DURATION = 220


def make_fonts():
    return {
        'sm': pygame.font.SysFont("dejavusans", FONT_SM, bold=False),
        'md': pygame.font.SysFont("dejavusans", FONT_MD, bold=True),
        'lg': pygame.font.SysFont("dejavusans", FONT_LG, bold=True),
    }


# ─────────────────────────────────────────────
#  Écran de sélection (mode + niveau)
# ─────────────────────────────────────────────
def selection_screen(screen: pygame.Surface, fonts: dict) -> dict:
    """
    Affiche un menu de sélection.
    Retourne {'mode': '2joueurs'|'vsIA', 'level': int, 'ai_player': 0|1}
    """
    clock  = pygame.time.Clock()
    modes  = ['2 Joueurs', 'Joueur vs IA']
    levels = list(LEVELS.keys())          # ['facile','moyen','difficile','expert']
    sides  = ['Je joue J1 (bleu)', 'Je joue J2 (rouge)']

    sel_mode  = 0   # index dans modes
    sel_level = 1   # index dans levels  (moyen par défaut)
    sel_side  = 0   # 0 = humain est J1, 1 = humain est J2

    W, H   = screen.get_size()
    CENTER = W // 2

    def btn(surface, text, rect, active, hover, fnt, dot_color=None):
        if active:
            bg, border_clr, text_clr, bw = (50, 65, 40), ACCENT, ACCENT, 2
        elif hover:
            bg, border_clr, text_clr, bw = BUTTON_HOVER_BG, TEXT_CLR, TEXT_CLR, 2
        else:
            bg, border_clr, text_clr, bw = (30, 30, 46), TEXT_DIM, TEXT_DIM, 1
        pygame.draw.rect(surface, bg, rect, border_radius=8)
        pygame.draw.rect(surface, border_clr, rect, bw, border_radius=8)
        lbl = fnt.render(text, True, text_clr)
        surface.blit(lbl, lbl.get_rect(center=rect.center))
        if dot_color:
            pygame.draw.circle(surface, dot_color, (rect.left + 20, rect.centery), 8)

    while True:
        now    = pygame.time.get_ticks()
        mx, my = pygame.mouse.get_pos()
        screen.fill(BG)

        # ── Étoiles décoratives ──
        for _si in range(28):
            _sx = (_si * 283) % (W - 40) + 20
            _sy = (_si * 197) % (H - 40) + 20
            _sa = max(0, min(255, int(12 + 18 * math.sin(now / 500 + _si * 1.3))))
            _sr = 1 if _si % 3 != 0 else 2
            _ss = pygame.Surface((_sr * 2 + 2, _sr * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(_ss, (180, 190, 255, _sa), (_sr + 1, _sr + 1), _sr)
            screen.blit(_ss, (_sx - _sr, _sy - _sr))

        # ── Titre animé ──
        pulse     = 0.75 + 0.25 * math.sin(now / 700)
        title_clr = (int(ACCENT[0] * pulse), int(ACCENT[1] * pulse), int(ACCENT[2] * pulse))
        t = fonts['lg'].render("QUORIDOR", True, title_clr)
        screen.blit(t, t.get_rect(centerx=CENTER, top=40))
        sub = fonts['sm'].render("Université de Rouen  —  M1 GIL", True, TEXT_DIM)
        screen.blit(sub, sub.get_rect(centerx=CENTER, top=86))

        y = 140
        # ── Mode ──
        card_mode = pygame.Rect(CENTER - 175, y - 8, 350, 40 + len(modes) * 52 + 4)
        pygame.draw.rect(screen, SECTION_BG, card_mode, border_radius=10)
        pygame.draw.rect(screen, (40, 42, 65), card_mode, 1, border_radius=10)
        lbl = fonts['md'].render("Mode de jeu", True, TEXT_CLR)
        screen.blit(lbl, lbl.get_rect(centerx=CENTER, top=y))
        y += 40
        mode_rects = []
        for i, m in enumerate(modes):
            r = pygame.Rect(CENTER - 160, y, 320, 42)
            mode_rects.append(r)
            btn(screen, m, r, sel_mode == i, r.collidepoint(mx, my), fonts['md'])
            y += 52

        # ── Niveau (seulement si vs IA) ──
        level_rects = []
        side_rects  = []
        if sel_mode == 1:
            y += 10
            card_ia = pygame.Rect(CENTER - 175, y - 8,
                                  350, 44 + len(levels) * 48 + 50 + len(sides) * 48 + 4)
            pygame.draw.rect(screen, SECTION_BG, card_ia, border_radius=10)
            pygame.draw.rect(screen, (40, 42, 65), card_ia, 1, border_radius=10)
            lbl = fonts['md'].render("Niveau IA", True, TEXT_CLR)
            screen.blit(lbl, lbl.get_rect(centerx=CENTER, top=y))
            y += 40
            for i, lv in enumerate(levels):
                r = pygame.Rect(CENTER - 140, y, 280, 38)
                level_rects.append(r)
                btn(screen, lv.capitalize(), r, sel_level == i,
                    r.collidepoint(mx, my), fonts['sm'])
                y += 48

            y += 6
            lbl = fonts['md'].render("Votre couleur", True, TEXT_CLR)
            screen.blit(lbl, lbl.get_rect(centerx=CENTER, top=y))
            y += 40
            for i, s in enumerate(sides):
                clr_dot = P1_CLR if i == 0 else P2_CLR
                r = pygame.Rect(CENTER - 160, y, 320, 38)
                side_rects.append(r)
                btn(screen, s, r, sel_side == i, r.collidepoint(mx, my),
                    fonts['sm'], dot_color=clr_dot)
                y += 48

        # ── Bouton Jouer ──
        y += 16
        play_r   = pygame.Rect(CENTER - 130, y, 260, 54)
        play_hov = play_r.collidepoint(mx, my)
        play_bg  = (min(255, ACCENT[0] + 30), min(255, ACCENT[1] + 30),
                    min(255, ACCENT[2] + 30)) if play_hov else ACCENT
        pygame.draw.rect(screen, (10, 12, 20), play_r.move(0, 4), border_radius=12)
        pygame.draw.rect(screen, play_bg, play_r, border_radius=12)
        pygame.draw.rect(screen, (255, 255, 255) if play_hov else (180, 180, 180),
                         play_r, 2, border_radius=12)

        # ── Icône Play dessinée ──
        icon_x = play_r.centerx - 55
        icon_y = play_r.centery

        pygame.draw.circle(
            screen,
            (255, 255, 255),
            (icon_x, icon_y),
            16
        )

        pygame.draw.polygon(
            screen,
            BG,
            [
                (icon_x - 4, icon_y - 7),
                (icon_x - 4, icon_y + 7),
                (icon_x + 8, icon_y),
            ]
        )

        # ── Texte ──
        lbl_s = fonts['md'].render("JOUER", True, BG)

        screen.blit(
            lbl_s,
            (
                play_r.centerx - lbl_s.get_width() // 2 + 20,
                play_r.centery - lbl_s.get_height() // 2
            )
)


        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, r in enumerate(mode_rects):
                    if r.collidepoint(mx, my):
                        sel_mode = i
                for i, r in enumerate(level_rects):
                    if r.collidepoint(mx, my):
                        sel_level = i
                for i, r in enumerate(side_rects):
                    if r.collidepoint(mx, my):
                        sel_side = i
                if play_r.collidepoint(mx, my):
                    depth     = list(LEVELS.values())[sel_level]
                    ai_player = 1 - sel_side
                    return {
                        'mode':      modes[sel_mode],
                        'level':     depth,
                        'ai_player': ai_player,
                        'vs_ai':     sel_mode == 1,
                    }


# ─────────────────────────────────────────────
#  Boucle principale
# ─────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Quoridor — M1 GIL | Université de Rouen")
    icon = pygame.Surface((32, 32)); icon.fill(ACCENT)
    pygame.display.set_icon(icon)

    fonts = make_fonts()
    sfx   = Sounds()          # sons procéduraux

    # Score session [J1_wins, J2_wins]
    scores = [0, 0]

    # Sélection mode/niveau
    cfg = selection_screen(screen, fonts)

    gs         = GameState()
    clock      = pygame.time.Clock()
    horizontal = True

    vs_ai     = cfg['vs_ai']
    ai_player = cfg['ai_player']
    ai_depth  = cfg['level']

    # ── État thread IA ────────────────────────
    ai_thinking = False   # calcul en cours
    ai_result   = [None]  # partagé avec le thread

    def run_ai():
        ai_result[0] = best_move(gs, ai_depth)

    valid = gs.valid_moves()

    # ── Animation pion ────────────────────────
    anim_player   = None    # 0 ou 1 : quel pion anime
    anim_start_px = (0, 0)  # pixel départ
    anim_end_px   = (0, 0)  # pixel arrivée
    anim_start_t  = 0       # tick de départ

    def start_anim(player_idx: int, from_col, from_row, to_col, to_row):
        nonlocal anim_player, anim_start_px, anim_end_px, anim_start_t
        anim_player   = player_idx
        anim_start_px = cell_rect(from_col, from_row).center
        anim_end_px   = cell_rect(to_col,   to_row).center
        anim_start_t  = pygame.time.get_ticks()

    def pawn_pixel(player_idx: int) -> tuple | None:
        """Retourne la position pixel si ce pion est en cours d'animation."""
        if anim_player != player_idx:
            return None
        now = pygame.time.get_ticks()
        t   = min(1.0, (now - anim_start_t) / ANIM_DURATION)
        # Easing : ease-out quadratique
        t   = 1 - (1 - t) ** 2
        cx  = int(anim_start_px[0] + (anim_end_px[0] - anim_start_px[0]) * t)
        cy  = int(anim_start_px[1] + (anim_end_px[1] - anim_start_px[1]) * t)
        return (cx, cy)

    valid = gs.valid_moves()

    def apply_move_with_anim(player_idx, col, row):
        nonlocal valid
        old_col, old_row = gs.positions[player_idx]
        ok = gs.apply_move(col, row)
        if ok:
            start_anim(player_idx, old_col, old_row, col, row)
            sfx.play_move()
            gs.move_mode = True   # le prochain joueur commence toujours en mode déplacement
        valid = gs.valid_moves() if gs.winner is None else []
        return ok

    def apply_wall_action(r, c, horiz):
        nonlocal valid
        gs.apply_wall(r, c, horiz)
        gs.move_mode = True
        sfx.play_wall()
        valid = gs.valid_moves() if gs.winner is None else []

    # ─────────────────────────────────────────
    while True:
        now    = pygame.time.get_ticks()
        mx, my = pygame.mouse.get_pos()

        # ── Fin d'animation ───────────────────
        if anim_player is not None and (now - anim_start_t) >= ANIM_DURATION:
            anim_player = None

        human_turn = (not vs_ai) or (gs.current != ai_player)

        # ── Lancer le calcul IA ───────────────
        if (vs_ai and gs.winner is None
                and gs.current == ai_player
                and not ai_thinking):
            ai_thinking  = True
            ai_result[0] = None
            valid        = []
            threading.Thread(target=run_ai, daemon=True).start()

        # ── Résultat IA reçu → appliquer ──────
        if ai_thinking and ai_result[0] is not None:
            ai_thinking = False
            action = ai_result[0]
            ai_result[0] = None
            if action:
                if action[0] == 'move':
                    apply_move_with_anim(ai_player, action[1], action[2])
                    record_position(action[1], action[2])
                else:
                    apply_wall_action(action[1], action[2], action[3])
            if gs.winner is not None:
                scores[gs.winner] += 1
                sfx.play_win()

        # ── Événements ────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_QUESTION or event.key == pygame.K_SLASH:
                    draw_rules_screen(screen, fonts)

                elif event.key == pygame.K_ESCAPE:
                    cfg         = selection_screen(screen, fonts)
                    gs          = GameState()
                    horizontal  = True
                    vs_ai       = cfg['vs_ai']
                    ai_player   = cfg['ai_player']
                    ai_depth    = cfg['level']
                    ai_thinking = False
                    ai_result[0] = None
                    anim_player = None
                    reset_history()
                    valid       = gs.valid_moves()
                    continue

                elif event.key == pygame.K_r:
                    gs          = GameState()
                    horizontal  = True
                    ai_thinking = False
                    ai_result[0] = None
                    anim_player = None
                    reset_history()
                    valid       = gs.valid_moves()

                elif human_turn and gs.winner is None:
                    if event.key == pygame.K_b:
                        # B : entrer/sortir du mode barrière
                        if gs.walls_left[gs.current] > 0:
                            gs.move_mode = not gs.move_mode
                            valid = gs.valid_moves() if gs.move_mode else []
                    elif event.key == pygame.K_h:
                        horizontal = not horizontal

            elif event.type == pygame.MOUSEBUTTONDOWN and gs.winner is None:
                current_human_turn = (not vs_ai) or (gs.current != ai_player)
                if not current_human_turn:
                    continue
                if event.button == 1:   # clic gauche
                    if gs.move_mode:
                        cell = pixel_to_cell(mx, my)
                        if cell and cell in valid:
                            prev = gs.current
                            apply_move_with_anim(prev, cell[0], cell[1])
                            if gs.winner is not None:
                                scores[gs.winner] += 1
                                sfx.play_win()
                                pass
                    else:
                        # mode barrière : poser si le ghost est valide
                        wh = wall_from_pixel(mx, my, horizontal)
                        if wh and gs.can_place_wall(*wh, horizontal):
                            apply_wall_action(*wh, horizontal)

        # ── Calcul des indicateurs de rendu ───
        # (APRÈS les events : état stable, pas de flash)
        human_turn = (not vs_ai) or (gs.current != ai_player)
        hovered   = pixel_to_cell(mx, my)
        # Important : pendant le tour IA, on force l'affichage en mode déplacement
        # pour éviter tout "flash" visuel de barrière.
        wall_mode = (not gs.move_mode) and human_turn

        wall_hover = None
        wall_valid = False
        if (wall_mode and human_turn and gs.winner is None
                and not ai_thinking and anim_player is None
                and gs.walls_left[gs.current] > 0):
            wall_hover = wall_from_pixel(mx, my, horizontal)
            if wall_hover:
                wall_valid = gs.can_place_wall(*wall_hover, horizontal)

        # ── Rendu ─────────────────────────────
        screen.fill(BG)

        show_hints = (gs.move_mode and human_turn
                      and gs.winner is None and anim_player is None)
        draw_board(screen,
                   valid_moves=valid if show_hints else [],
                   hovered=hovered   if show_hints else None,
                   active_pos=gs.current_pos if gs.winner is None else None)

        if show_hints:
            draw_move_direction_arrows(screen, gs.current_pos, valid)

        draw_coordinates(screen, fonts['sm'])
        draw_walls(screen, gs.h_walls, gs.v_walls)

        if wall_hover:
            draw_wall_ghost(screen, *wall_hover, horizontal, wall_valid)

        p0, p1 = gs.positions
        draw_pawn(screen, *p0, P1_CLR, P1_DARK, "J1", fonts['md'],
                  active=(gs.current == 0 and gs.winner is None),
                  pixel_pos=pawn_pixel(0))
        draw_pawn(screen, *p1, P2_CLR, P2_DARK, "J2", fonts['md'],
                  active=(gs.current == 1 and gs.winner is None),
                  pixel_pos=pawn_pixel(1))

        ps = gs.panel_state()
        ps['scores'] = scores
        if vs_ai:
            level_name = [k for k, v in LEVELS.items() if v == ai_depth][0]
            ps['ai_label'] = f"J{ai_player+1} = IA ({level_name})"
        if ai_thinking:
            ps['status'] = "IA réfléchit..."

        draw_panel(screen, fonts, ps)

        if gs.winner is None:
            draw_mode_badge(screen, fonts['sm'], wall_mode, horizontal,
                            gs.walls_left[gs.current])

        if gs.winner is not None:
            draw_winner_banner(screen, fonts, gs.winner)

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
