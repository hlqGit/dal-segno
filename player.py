import pygame
import mido

pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
running = True

# ------ VARIABLES DEFINED HERE ------

# for playing music
music_filepath = "midi files/chpn_op23.mid"
# for parsing music
midi_file = mido.MidiFile(music_filepath)

# play music event 
PLAY_MUSIC_EVENT = pygame.USEREVENT + 1

# --- RENDERING VARS --- 

scroll_speed = 50

# ----------------------

white_key_width = screen.get_width()//52
white_key_height = 125
key_gap = 1

black_key_width = white_key_width - 12
black_key_height = 75
black_key_pattern = [1, 1, 0, 1, 1, 1, 0]

screen_height = screen.get_height()
screen_width = screen.get_width()
# ------------------------------------

# ------ COLORS DEFINED HERE ------

background = "orchid3"

white_key_color = "white"
black_key_color = "black"

white_press_color = "cyan2"
black_press_color = "cyan4"

# ---------------------------------

pygame.mixer.music.load(music_filepath)
pygame.time.set_timer(PLAY_MUSIC_EVENT, 3000)

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

    # draws the white keys of the piano
    for i in range(52):
        start = (i * screen.get_width()) / 52
        end = ((i + 1) * screen.get_width()) / 52

        x_pos = int(start) + (key_gap//2)
        key_w = int(end) - int(start) - key_gap

        pygame.draw.rect(screen, "white",
                        (x_pos, screen_height - white_key_height, key_w, white_key_height))

    # draws the black keys of the piano (51 cuz no last black key)
    for i in range(51):
        pattern_index = (i+5) % 7

        if black_key_pattern[pattern_index] == 1:
            seam = ((i + 1) * screen.get_width()) / 52
            x_pos = int(seam) - (black_key_width // 2)
            pygame.draw.rect(screen, "black",
                            (x_pos, screen_height-white_key_height, black_key_width, black_key_height))

    pygame.display.flip()
    dt = clock.tick(60) / 1000

pygame.quit()