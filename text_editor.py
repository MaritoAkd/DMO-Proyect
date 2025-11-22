import pygame
import os
import bmo_gui as gui

class TextEditor:
    def __init__(self, title, file_path):
        self.title = title
        self.file_path = file_path
        self.text_lines = []
        self.cursor_line = 0
        self.cursor_col = 0
        self.scroll_offset = 0
        self.horizontal_scroll = 0
        self.is_active = False
        self.font = pygame.font.SysFont("Courier New", 18)
        self.title_font = pygame.font.SysFont("Arial", 32, bold=True)
        self.button_font = pygame.font.SysFont("Arial", 20)
        self.line_height = self.font.get_height() + 4
        self.cursor_blink_time = 0
        self.cursor_visible = True
        self.max_line_length = 120
        
        # Colores sobrios y coherentes con GUI
        self.text_color = (220, 220, 214)  # texto casi blanco, menos brillante
        self.cursor_color = (180, 200, 180)  # cursor suave
        self.title_color = (220, 220, 214)  # título neutro, igual tono que texto
        self.line_number_color = (120, 120, 120)
        self.button_color = (40, 40, 48, 200)
        self.button_hover_color = (60, 60, 68, 220)
        # Hover activo del botón (guardar): un verde claro y suave
        self.button_active_color = (170, 225, 185, 200)
        self.button_text_color = (230, 230, 230)

        self.load_file()
    
    def load_file(self):
        """Carga el contenido del archivo"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.text_lines = content.split('\n') if content else [""]
            else:
                self.text_lines = [""]
        except Exception as e:
            print(f"Error cargando {self.file_path}: {e}")
            self.text_lines = [f"Error cargando archivo: {e}"]
    
    def save_file(self):
        """Guarda el contenido al archivo"""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write('\n'.join(self.text_lines))
            return True
        except Exception as e:
            print(f"Error guardando {self.file_path}: {e}")
            return False
    
    def handle_event(self, event, screen_rect, background_image=None):
        """Maneja eventos de teclado y mouse"""
        if not self.is_active:
            return None
        
        editor_rect = self.get_editor_rect(screen_rect)
        text_area_y = 100
        text_area_height = editor_rect.height - 180
        visible_lines = int(text_area_height / self.line_height)
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check botones
            save_button, close_button = self.get_button_rects(editor_rect)
            
            if save_button.collidepoint(event.pos):
                if self.save_file():
                    return "SAVED"
            elif close_button.collidepoint(event.pos):
                return "CLOSE"
        
        elif event.type == pygame.KEYDOWN:
            # Preferir el mod del evento (más fiable) y fallback a get_mods
            mods = getattr(event, 'mod', pygame.key.get_mods())
            
            if event.key == pygame.K_ESCAPE:
                return "CLOSE"
            
            # Ctrl+S para guardar
            elif event.key == pygame.K_s and (mods & pygame.KMOD_CTRL):
                if self.save_file():
                    return "SAVED"
            
            # Alt + Flechas para navegación rápida (mejor comportamiento)
            elif (mods & pygame.KMOD_ALT) and event.key == pygame.K_DOWN:
                # Bajar una página visible (visible_lines)
                max_scroll = max(0, len(self.text_lines) - visible_lines)
                self.scroll_offset = min(max_scroll, self.scroll_offset + visible_lines)

            elif (mods & pygame.KMOD_ALT) and event.key == pygame.K_UP:
                # Subir una página visible
                self.scroll_offset = max(0, self.scroll_offset - visible_lines)

            elif (mods & pygame.KMOD_ALT) and event.key == pygame.K_RIGHT:
                # Mover a la derecha horizontalmente (paso mayor)
                self.horizontal_scroll += 10

            elif (mods & pygame.KMOD_ALT) and event.key == pygame.K_LEFT:
                # Mover a la izquierda horizontalmente
                self.horizontal_scroll = max(0, self.horizontal_scroll - 10)
            
            # Navegación normal
            elif event.key == pygame.K_UP:
                self.cursor_line = max(0, self.cursor_line - 1)
                self.cursor_col = min(self.cursor_col, len(self.text_lines[self.cursor_line]))
            
            elif event.key == pygame.K_DOWN:
                self.cursor_line = min(len(self.text_lines) - 1, self.cursor_line + 1)
                self.cursor_col = min(self.cursor_col, len(self.text_lines[self.cursor_line]))
            
            elif event.key == pygame.K_LEFT:
                if self.cursor_col > 0:
                    self.cursor_col -= 1
                elif self.cursor_line > 0:
                    self.cursor_line -= 1
                    self.cursor_col = len(self.text_lines[self.cursor_line])
            
            elif event.key == pygame.K_RIGHT:
                if self.cursor_col < len(self.text_lines[self.cursor_line]):
                    self.cursor_col += 1
                elif self.cursor_line < len(self.text_lines) - 1:
                    self.cursor_line += 1
                    self.cursor_col = 0
            
            elif event.key == pygame.K_HOME:
                self.cursor_col = 0
            
            elif event.key == pygame.K_END:
                self.cursor_col = len(self.text_lines[self.cursor_line])
            
            elif event.key == pygame.K_PAGEUP:
                self.cursor_line = max(0, self.cursor_line - visible_lines)
                self.cursor_col = min(self.cursor_col, len(self.text_lines[self.cursor_line]))
            
            elif event.key == pygame.K_PAGEDOWN:
                self.cursor_line = min(len(self.text_lines) - 1, self.cursor_line + visible_lines)
                self.cursor_col = min(self.cursor_col, len(self.text_lines[self.cursor_line]))
            
            # Edición
            elif event.key == pygame.K_RETURN:
                current_line = self.text_lines[self.cursor_line]
                self.text_lines[self.cursor_line] = current_line[:self.cursor_col]
                self.text_lines.insert(self.cursor_line + 1, current_line[self.cursor_col:])
                self.cursor_line += 1
                self.cursor_col = 0
            
            elif event.key == pygame.K_BACKSPACE:
                if self.cursor_col > 0:
                    line = self.text_lines[self.cursor_line]
                    self.text_lines[self.cursor_line] = line[:self.cursor_col-1] + line[self.cursor_col:]
                    self.cursor_col -= 1
                elif self.cursor_line > 0:
                    prev_line = self.text_lines[self.cursor_line - 1]
                    current_line = self.text_lines[self.cursor_line]
                    self.cursor_col = len(prev_line)
                    self.text_lines[self.cursor_line - 1] = prev_line + current_line
                    self.text_lines.pop(self.cursor_line)
                    self.cursor_line -= 1
            
            elif event.key == pygame.K_DELETE:
                if self.cursor_col < len(self.text_lines[self.cursor_line]):
                    line = self.text_lines[self.cursor_line]
                    self.text_lines[self.cursor_line] = line[:self.cursor_col] + line[self.cursor_col+1:]
                elif self.cursor_line < len(self.text_lines) - 1:
                    current_line = self.text_lines[self.cursor_line]
                    next_line = self.text_lines[self.cursor_line + 1]
                    self.text_lines[self.cursor_line] = current_line + next_line
                    self.text_lines.pop(self.cursor_line + 1)
            
            # Texto normal
            elif event.unicode and event.unicode.isprintable():
                if len(self.text_lines[self.cursor_line]) < self.max_line_length:
                    line = self.text_lines[self.cursor_line]
                    self.text_lines[self.cursor_line] = line[:self.cursor_col] + event.unicode + line[self.cursor_col:]
                    self.cursor_col += 1

        # Asegurar que horizontal_scroll no sea negativo y no demasiado grande
        self.horizontal_scroll = max(0, self.horizontal_scroll)
        
        return None
    
    def get_editor_rect(self, screen_rect):
        """Calcula el rectángulo del editor"""
        width = int(screen_rect.width * 0.85)
        height = int(screen_rect.height * 0.85)
        x = (screen_rect.width - width) // 2
        y = (screen_rect.height - height) // 2
        return pygame.Rect(x, y, width, height)
    
    def get_button_rects(self, editor_rect):
        """Calcula rectángulos de botones"""
        button_width = 180
        button_height = 50
        button_y = editor_rect.bottom - button_height - 25
        
        save_button = pygame.Rect(
            editor_rect.centerx - button_width - 15,
            button_y,
            button_width,
            button_height
        )
        
        close_button = pygame.Rect(
            editor_rect.centerx + 15,
            button_y,
            button_width,
            button_height
        )
        
        return save_button, close_button
    
    def update(self, dt):
        """Actualiza animaciones"""
        self.cursor_blink_time += dt
        if self.cursor_blink_time >= 0.5:
            self.cursor_visible = not self.cursor_visible
            self.cursor_blink_time = 0
        
        # Ajustar scroll para mantener cursor visible
        visible_lines = 25
        
        if self.cursor_line < self.scroll_offset:
            self.scroll_offset = self.cursor_line
        elif self.cursor_line >= self.scroll_offset + visible_lines:
            self.scroll_offset = self.cursor_line - visible_lines + 1
    
    def draw(self, surface, screen_rect, background_image=None):
        """Dibuja el editor"""
        if not self.is_active:
            return
        
        editor_rect = self.get_editor_rect(screen_rect)
        
        # Crear superficie para el editor
        editor_surface = pygame.Surface((editor_rect.width, editor_rect.height), pygame.SRCALPHA)
        
        # Dibujar un panel oscuro semitransparente para el editor, de modo que el fondo global (ya bliteado en VENTANA)
        # sea visible detrás del panel. Si se pasa background_image y se desea el recorte original, el
        # código anterior puede volver a activarse como fallback.
        panel = pygame.Surface((editor_rect.width, editor_rect.height), pygame.SRCALPHA)
        panel.fill((8, 8, 12, 200))  # panel oscuro semi-transparente
        # Borde suave
        pygame.draw.rect(panel, (30, 30, 40, 220), (0, 0, editor_rect.width, editor_rect.height), width=2, border_radius=20)
        editor_surface.blit(panel, (0, 0))

        # Si explícitamente se pasa una imagen de fondo y se quiere usar como recorte, usarla como fallback
        if background_image:
            try:
                base_w = background_image.get_width()
                base_h = background_image.get_height()
                scale = min(gui.ANCHO_PANTALLA / base_w, gui.ALTO_PANTALLA / base_h)
                full_w = int(base_w * scale)
                full_h = int(base_h * scale)
                scaled_full = pygame.transform.smoothscale(background_image, (full_w, full_h))
                base_rect = scaled_full.get_rect(center=gui.VENTANA.get_rect().center)
                bg_crop = pygame.Surface((editor_rect.width, editor_rect.height), pygame.SRCALPHA)
                blit_x = base_rect.left - editor_rect.left
                blit_y = base_rect.top - editor_rect.top
                bg_crop.blit(scaled_full, (blit_x, blit_y))
                # Aplicar el recorte con baja opacidad sobre el panel para reforzar el look
                bg_crop.set_alpha(80)
                editor_surface.blit(bg_crop, (0, 0))
            except Exception:
                pass
        
        # Borde elegante
        pygame.draw.rect(editor_surface, self.title_color, 
                        (0, 0, editor_rect.width, editor_rect.height), 
                        width=3, border_radius=20)
        
        # Título
        title_surf = self.title_font.render(self.title, True, self.title_color)
        editor_surface.blit(title_surf, (30, 30))
        
        # Área de texto
        text_area_y = 100
        text_area_height = editor_rect.height - 180
        text_area_rect = pygame.Rect(30, text_area_y, editor_rect.width - 60, text_area_height)
        
        # Fondo del área de texto
        text_bg = pygame.Surface((text_area_rect.width, text_area_rect.height), pygame.SRCALPHA)
        text_bg.fill((10, 10, 15, 180))
        pygame.draw.rect(text_bg, (50, 50, 60, 100), 
                        (0, 0, text_area_rect.width, text_area_rect.height), 
                        width=2, border_radius=12)
        editor_surface.blit(text_bg, text_area_rect.topleft)
        
        # Dibujar líneas de texto
        visible_lines = int(text_area_height / self.line_height)
        start_line = self.scroll_offset
        end_line = min(len(self.text_lines), start_line + visible_lines)
        
        for i in range(start_line, end_line):
            line_text = self.text_lines[i]
            y_pos = text_area_y + 15 + (i - start_line) * self.line_height
            
            # Highlight de la línea actual
            if i == self.cursor_line:
                highlight = pygame.Surface((text_area_rect.width - 10, self.line_height), pygame.SRCALPHA)
                highlight.fill((100, 200, 255, 20))
                editor_surface.blit(highlight, (text_area_rect.left + 5, y_pos - 2))
            
            # Número de línea
            line_num_surf = self.font.render(f"{i+1:4d}", True, self.line_number_color)
            editor_surface.blit(line_num_surf, (35, y_pos))
            
            # Texto de la línea (con scroll horizontal)
            if line_text:
                # Aplicar scroll horizontal
                visible_text = line_text[self.horizontal_scroll:]
                text_surf = self.font.render(visible_text, True, self.text_color)
                editor_surface.blit(text_surf, (90, y_pos))
            
            # Cursor
            if i == self.cursor_line and self.cursor_visible:
                # Ajustar posición del cursor con scroll horizontal
                visible_col = max(0, self.cursor_col - self.horizontal_scroll)
                cursor_text = line_text[self.horizontal_scroll:self.cursor_col]
                cursor_x = 90 + self.font.size(cursor_text)[0]
                pygame.draw.line(editor_surface, self.cursor_color, 
                               (cursor_x, y_pos), 
                               (cursor_x, y_pos + self.line_height - 4), 3)
        
        # Botones
        save_button, close_button = self.get_button_rects(editor_rect)
        mouse_pos = pygame.mouse.get_pos()
        
        save_button_rel = save_button.move(-editor_rect.left, -editor_rect.top)
        close_button_rel = close_button.move(-editor_rect.left, -editor_rect.top)
        
        # Botón Guardar
        save_hover = save_button.collidepoint(mouse_pos)
        save_color = self.button_active_color if save_hover else self.button_color
        pygame.draw.rect(editor_surface, save_color, save_button_rel, border_radius=12)
        if save_hover:
            pygame.draw.rect(editor_surface, self.title_color, save_button_rel, width=2, border_radius=12)
        
        save_text = self.button_font.render("Guardar", True, self.button_text_color)
        save_text_rect = save_text.get_rect(center=save_button_rel.center)
        editor_surface.blit(save_text, save_text_rect)
        
        save_hint = pygame.font.SysFont("Arial", 14).render("Ctrl+S", True, (150, 150, 150))
        editor_surface.blit(save_hint, (save_button_rel.centerx - save_hint.get_width()//2, 
                                       save_button_rel.bottom + 5))
        
        # Botón Cerrar
        close_hover = close_button.collidepoint(mouse_pos)
        close_color = self.button_hover_color if close_hover else self.button_color
        pygame.draw.rect(editor_surface, close_color, close_button_rel, border_radius=12)
        if close_hover:
            pygame.draw.rect(editor_surface, (200, 100, 100), close_button_rel, width=2, border_radius=12)
        
        close_text = self.button_font.render("Cerrar", True, self.button_text_color)
        close_text_rect = close_text.get_rect(center=close_button_rel.center)
        editor_surface.blit(close_text, close_text_rect)
        
        close_hint = pygame.font.SysFont("Arial", 14).render("ESC", True, (150, 150, 150))
        editor_surface.blit(close_hint, (close_button_rel.centerx - close_hint.get_width()//2, 
                                        close_button_rel.bottom + 5))
        
        # Info adicional
        info_text = f"Linea {self.cursor_line + 1}/{len(self.text_lines)} | Col {self.cursor_col + 1}"
        info_surf = pygame.font.SysFont("Arial", 16).render(info_text, True, (150, 150, 150))
        editor_surface.blit(info_surf, (editor_rect.width - info_surf.get_width() - 30, 35))
        
        # Ayuda de navegación
        help_text = "Alt+Flechas: Navegacion rapida"
        help_surf = pygame.font.SysFont("Arial", 14).render(help_text, True, (120, 120, 120))
        editor_surface.blit(help_surf, (30, editor_rect.height - 25))
        
        surface.blit(editor_surface, editor_rect.topleft)
    
    def open(self):
        """Activa el editor"""
        self.load_file()
        self.is_active = True
        self.cursor_line = 0
        self.cursor_col = 0
        self.scroll_offset = 0
        self.horizontal_scroll = 0
    
    def close(self):
        """Cierra el editor"""
        self.is_active = False