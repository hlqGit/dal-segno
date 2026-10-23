import pygame
import audioproc

pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
running = True

# ------ VARIABLES DEFINED HERE ------

music_filepath = "midi files/clair-de-lune-debussy.mid"

# play music event 
PLAY_MUSIC_EVENT = pygame.USEREVENT + 1

# --- RENDERING VARS --- 

scroll_speed = 300

# ----------------------

white_key_width = screen.get_width()//52
white_key_height = 125
key_gap = 1

black_key_width = white_key_width - 12
black_key_height = 75
black_key_pattern = [1, 1, 0, 1, 1, 1, 0]

screen_height = screen.get_height()
screen_width = screen.get_width()

hit_line_y = screen_height - white_key_height

white_notes = [a for a in range (21, 109) if a % 12 in [0, 2, 4, 5, 7, 9, 11]]
pitch_data = {}

# ------------------------------------

# ------ COLORS DEFINED HERE ------

background = "lightblue"

white_key_color = "white"
black_key_color = "black"

white_press_color = "cyan2"
black_press_color = "cyan4"

falling_block_white = "lightcoral"
falling_block_black = "indianred4"

# ---------------------------------

pygame.mixer.music.load(music_filepath)
pygame.time.set_timer(PLAY_MUSIC_EVENT, 3000)
extracted_notes = audioproc.extract_notes(music_filepath)

# pre-calculate white keys
for i in range(52):
    start = (i * screen.get_width()) / 52
    end = ((i + 1) * screen.get_width()) / 52
    
    x_pos = int(start) + (key_gap // 2)
    key_w = int(end) - int(start) - key_gap
    
    pitch_data[white_notes[i]] = {'x': x_pos, 'w': key_w}

# pre-calculate black keys
for i in range(51): 
    pattern_index = (i + 5) % 7
    if black_key_pattern[pattern_index] == 1:
        seam = ((i + 1) * screen.get_width()) / 52
        x_pos = int(seam) - (black_key_width // 2)
        
        black_pitch = white_notes[i] + 1
        pitch_data[black_pitch] = {'x': x_pos, 'w': black_key_width}

# ------------------- MAIN GAME LOOP -------------------

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == PLAY_MUSIC_EVENT:
            pygame.mixer.music.play()
            pygame.time.set_timer(PLAY_MUSIC_EVENT, 0)

    # fill the screen with a color to wipe away anything from last frame
    screen.fill(background)

    # put black behind the piano so that the gaps are black
    pygame.draw.rect(screen, "black", (0, screen_height - white_key_height, screen_width, white_key_height))

    # ---------- FALLING BLOCKS DRAWN HERE ----------
    try:
        current_time = pygame.mixer.music.get_pos() / 1000.0
    except:
        current_time = 0

    for note in extracted_notes:
        if current_time < note['start'] + note['duration']:
            note_height = note['duration'] * scroll_speed
            distance_to_key = (note['start'] - current_time) * scroll_speed

            y_pos = hit_line_y - distance_to_key - note_height
            x_pos = pitch_data[note['pitch']]['x']
            note_width = pitch_data[note['pitch']]['w']

            if note['pitch'] in white_notes:
                pygame.draw.rect(screen, falling_block_white, (x_pos, y_pos, note_width, note_height), 0, 3)
            else:
                pygame.draw.rect(screen, falling_block_black, (x_pos, y_pos, note_width, note_height), 0, 3)
    # -----------------------------------------------

    active_pitches = set()
    for note in extracted_notes:
        if note['start'] <= current_time <= (note['start'] + note['duration']):
            active_pitches.add(note['pitch'])

    # ----------- DRAW THE KEYS HERE -----------
    # draws the white keys of the piano
    for i in range(52):
        start = (i * screen.get_width()) / 52
        end = ((i + 1) * screen.get_width()) / 52

        x_pos = int(start) + (key_gap//2)
        key_w = int(end) - int(start) - key_gap
        pygame.draw.rect(screen, white_key_color,
                        (x_pos, screen_height - white_key_height, key_w, white_key_height))

    # draws the ACTIVE white keys of the piano
    for pitch in active_pitches:
        # check if the pitch belongs to a white key using modulo 12
        if pitch % 12 in [0, 2, 4, 5, 7, 9, 11]: 
            x_pos = pitch_data[pitch]['x']
            key_w = pitch_data[pitch]['w']
            pygame.draw.rect(screen, white_press_color, 
                            (x_pos, screen_height - white_key_height, key_w, white_key_height))

    # draws the black keys of the piano (51 cuz no last black key)
    for i in range(51):
        pattern_index = (i+5) % 7

        if black_key_pattern[pattern_index] == 1:
            seam = ((i + 1) * screen.get_width()) / 52
            x_pos = int(seam) - (black_key_width // 2)
            
            pygame.draw.rect(screen, black_key_color,
                            (x_pos, screen_height-white_key_height, black_key_width, black_key_height))

    # draws the ACTIVE black keys of the piano
    for pitch in active_pitches:
        # Check if the pitch belongs to a black key
        if pitch % 12 in [1, 3, 6, 8, 10]:
            x_pos = pitch_data[pitch]['x']
            key_w = pitch_data[pitch]['w']
            pygame.draw.rect(screen, black_press_color, 
                            (x_pos, screen_height - white_key_height, key_w, black_key_height))
    
    # ------------------------------------------

    pygame.display.flip()
    dt = clock.tick(60) / 1000

pygame.quit()