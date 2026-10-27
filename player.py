import os
import pygame
import audioproc
import render

pygame.mixer.pre_init(render.SAMPLE_RATE, -16, 2)
pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
running = True

# ------ VARIABLES DEFINED HERE ------

music_filepath = "midi files/winter wind.mid"
music_save_path = "midi files/play.mid"
speeds = [0.5, 0.75, 1.0, 1.25, 1.5]
speed = 1.0  # the speed that is playing now
pending_speed = 1.0  # the speed picked with up/down, applied with Enter

PLAY_MUSIC_EVENT = pygame.USEREVENT + 1

scroll_speed = 500
start_delay = 2
paused = False
seek_step = 2  # seconds jumped by the left and right keys
seek_bar_font = pygame.font.Font(None, 30)

white_key_width = screen.get_width()//52
white_key_height = 125
key_gap = 1

black_key_width = white_key_width - 12
black_key_height = 85
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

seek_bar = "black"
seek_bar_progress = "crimson"

# ---------------------------------

extracted_notes = audioproc.extract_notes(music_filepath, music_save_path, start_delay)
song_length = max(note['start'] + note['duration'] for note in extracted_notes)

note_gap = 0.04  # seconds shaved off the end of every note so repeated notes show a gap
for note in extracted_notes:
    note['visual_duration'] = note['duration'] - min(note_gap, note['duration'] * 0.3)

loading_font = pygame.font.Font(None, 64)

def show_loading(fraction):
    pygame.event.pump()
    screen.fill(background)
    text = loading_font.render(f"Loading... {fraction:.0%}", True, "black")
    screen.blit(text, text.get_rect(center=screen.get_rect().center))
    pygame.display.flip()

# each song and speed gets its own cached wav
def wav_path_for(speed):
    return f"{os.path.splitext(music_filepath)[0]}_{speed}x.wav"

# loads the wav for a speed, rendering it first if it isn't cached yet
def load_song(speed):
    path = wav_path_for(speed)
    if not os.path.exists(path) or os.path.getmtime(path) < os.path.getmtime(music_filepath):
        show_loading(0)
        render.render_song(render.load_samples(), extracted_notes, path,
                           audioproc.extract_pedal(music_filepath, start_delay), show_loading, speed)
    return render.load_wav(path)

song_audio = load_song(speed)
song_playing = False  # becomes True once the start timer fires
base_time = 0.0  # song position (seconds) when the clock last restarted
base_tick = 0  # pygame ticks at that moment
song_channel = pygame.mixer.Channel(0)  # placeholder until play_from() starts the song

# the song clock only moves while the music is playing and not paused
def get_song_time():
    if not song_playing or paused:
        return base_time
    return min(base_time + (pygame.time.get_ticks() - base_tick) / 1000.0 * speed, song_total_length)

# plays the song from a position in seconds and restarts the clock there
def play_from(seconds):
    global song_sound, song_channel, base_time, base_tick, song_playing
    if song_playing:
        song_channel.stop()  # otherwise every seek adds another copy of the song
    song_sound =pygame.mixer.Sound(buffer=song_audio[int(seconds / speed * render.SAMPLE_RATE):])
    song_channel = song_sound.play()
    base_time, base_tick, song_playing = seconds, pygame.time.get_ticks(), True
    if paused:
        song_channel.pause()

pygame.time.set_timer(PLAY_MUSIC_EVENT, 500)

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
            play_from(0)
            song_total_length = song_sound.get_length()
            song_minutes, song_seconds = divmod(song_total_length, 60)
            pygame.time.set_timer(PLAY_MUSIC_EVENT, 0)

        elif event.type == pygame.KEYDOWN:

            # pause buttons 
            if event.key == pygame.K_SPACE and song_playing:
                if paused:
                    song_channel.unpause()
                    base_tick = pygame.time.get_ticks()
                else:
                    base_time = get_song_time()
                    song_channel.pause()
                paused = not paused

            # n
            elif event.key == pygame.K_n:
                print('norford')

            # handle seeking
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT) and song_playing:
                direction = 1 if event.key == pygame.K_RIGHT else -1
                new_time = min(max(get_song_time() + direction * seek_step, 0), song_length)
                play_from(new_time)

            # handle speed up and down
            elif event.key in (pygame.K_UP, pygame.K_DOWN):
                i = speeds.index(pending_speed) + (1 if event.key == pygame.K_UP else -1)
                pending_speed = speeds[min(max(i, 0), len(speeds) - 1)]

            # set pending speed equal to speed (lock in speed) and render if needed
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and song_playing and pending_speed != speed:
                position = min(get_song_time(), song_length)
                song_channel.stop()
                song_audio = load_song(pending_speed)
                speed = pending_speed
                play_from(position)  

            # cancel pending speed
            elif event.key == pygame.K_ESCAPE:
                pending_speed = speed

            elif event.key == pygame.K_r:
                play_from(0)

    # fill the screen with a color to wipe away anything from last frame
    screen.fill(background)

    # put black behind the piano so that the gaps are black
    pygame.draw.rect(screen, "black", (0, screen_height - white_key_height, screen_width, white_key_height))

    # ---------- FALLING BLOCKS DRAWN HERE ----------
    current_time = get_song_time()

    for note in extracted_notes:
        if current_time < note['start'] + note['visual_duration']:
            note_height = note['visual_duration'] * scroll_speed
            distance_to_key = (note['start'] - current_time) * scroll_speed

            y_pos = hit_line_y - distance_to_key - note_height
            x_pos = pitch_data[note['pitch']]['x']
            note_width = pitch_data[note['pitch']]['w']

            if note['pitch'] in white_notes:
                pygame.draw.rect(screen, falling_block_white, (x_pos + 1, y_pos, note_width - 2, note_height), 0, 3)
            else:
                pygame.draw.rect(screen, falling_block_black, (x_pos + 1, y_pos, note_width - 2, note_height), 0, 3)
    # -----------------------------------------------

    # gets all the current active notes to draw active (pressed) keys
    active_pitches = set()
    for note in extracted_notes:
        if note['start'] <= current_time < (note['start'] + note['visual_duration']):
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
                            (x_pos, screen_height-white_key_height, black_key_width, black_key_height), 0, 2)

    # draws the ACTIVE black keys of the piano
    for pitch in active_pitches:
        # Check if the pitch belongs to a black key
        if pitch % 12 in [1, 3, 6, 8, 10]:
            x_pos = pitch_data[pitch]['x']
            key_w = pitch_data[pitch]['w']
            pygame.draw.rect(screen, black_press_color, 
                            (x_pos, screen_height - white_key_height, key_w, black_key_height), 0, 2)
    
    # ------------------------------------------

    # ------- SEEK BAR -------
    pygame.draw.rect(screen, seek_bar, (0, 0, screen_width, 20))
    try:
        pygame.draw.rect(screen, seek_bar_progress, 
                        (0, 0, screen_width*(current_time/song_total_length), 20))
    except:
        pass
    song_current_time_min, song_current_time_sec = divmod(current_time, 60)
    try:
        seek_text = f"{int(song_current_time_min):02} : {int(song_current_time_sec):02}  /  {int(song_minutes):02} : {int(song_seconds):02}"
        text_surface = seek_bar_font.render(seek_text, True, seek_bar)
        screen.blit(text_surface, (20, 40))
    except:
        pass
    # ------------------------

    # ------- SPEED -------
    if speed == pending_speed:
        speed_text = f"{speed}x"
        speed_text_surface = seek_bar_font.render(speed_text, True, seek_bar)
        screen.blit(speed_text_surface, (20, 70))
    else:
        speed_text = f"{speed}x -> {pending_speed}x (press enter to confirm)"
        speed_text_surface = seek_bar_font.render(speed_text, True, seek_bar_progress)
        screen.blit(speed_text_surface, (20, 70))
    # ---------------------

    pygame.display.flip()
    dt = clock.tick(60) / 1000

pygame.quit()