import os
import wave
import numpy as np
import pygame

SAMPLE_DIR = "samples/salamander"
SAMPLE_RATE = 48000  # the salamander samples are 48 kHz
RELEASE = 0.5  # seconds a note takes to fade out after the key is released
VELOCITY_CURVE = 1.5  # higher = bigger volume gap between soft and loud notes

# semitone offset of each note name from C within an octave
NOTE_OFFSETS = {"C": 0, "Ds": 3, "Fs": 6, "A": 9}

"""
Converts a sample filename like 'Ds4.ogg' into its midi pitch number

Args:
    filename (string): The filename of the sample (A0.ogg, C4.ogg, Fs2.ogg, etc.)

Returns:
    int: The midi pitch (A0 = 21, C4 = 60)
"""
def filename_to_pitch(filename):
    name = os.path.splitext(filename)[0]
    note, octave = name[:-1], int(name[-1])
    return 12 * (octave + 1) + NOTE_OFFSETS[note]

"""
Loads every salamander sample into memory

Returns:
    dict: midi pitch -> numpy int16 array of shape (frames, channels)
"""
def load_samples():
    init = pygame.mixer.get_init()
    assert init, "call pygame.mixer.init() before load_samples()"
    channels = init[2]
    samples = {}

    for filename in os.listdir(SAMPLE_DIR):
        if filename.endswith(".ogg"):
            raw = pygame.mixer.Sound(os.path.join(SAMPLE_DIR, filename)).get_raw()
            samples[filename_to_pitch(filename)] = np.frombuffer(raw, dtype=np.int16).reshape(-1, channels)

    return samples

"""
Loads a wav file into memory

Args:
    path (string): The wav file to load

Returns:
    numpy array: int16 audio of shape (frames, 2)
"""
def load_wav(path):
    with wave.open(path, "rb") as wav:
        return np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16).reshape(-1, 2)

"""
Renders a single note from the nearest sample, pitch-shifted and cut to length

Args:
    samples (dict): The loaded samples from load_samples()
    pitch (int): The midi pitch of the note
    duration (float): How long the key is held, in seconds
    velocity (int): How hard the key is struck, from 1 to 127 (127 = full volume)

Returns:
    numpy array: float32 audio of shape (frames, channels), values from -1 to 1
"""
def render_note(samples, pitch, duration, velocity=127):
    sample_pitch = min(samples, key=lambda p: abs(p - pitch))
    sample = samples[sample_pitch]

    # playing the sample faster raises its pitch (12 semitones = double speed)
    ratio = 2 ** ((pitch - sample_pitch) / 12)

    # the note sounds while held, then fades out over RELEASE seconds
    length = int((duration + RELEASE) * SAMPLE_RATE)
    length = min(length, int((len(sample) - 1) / ratio))  # can't outlast the sample

    # read the sample at fractional positions to resample it
    positions = np.arange(length) * ratio
    source = np.arange(len(sample))
    shifted = np.stack([np.interp(positions, source, sample[:, c]) for c in range(sample.shape[1])], axis=1)

    envelope = np.ones(length)
    held = min(int(duration * SAMPLE_RATE), length)
    envelope[held:] = np.linspace(1, 0, length - held)

    gain = (velocity / 127) ** VELOCITY_CURVE

    return (shifted * envelope[:, None] * gain / 32768).astype(np.float32)

"""
Turns pedal events into the time ranges where the pedal is held down

Args:
    pedal (list): (time, is_down) tuples from audioproc.extract_pedal()
    end (float): When to release a pedal that is never let go, in seconds

Returns:
    list: (down_time, up_time) tuples, in order
"""
def pedal_intervals(pedal, end):
    intervals = []
    down_time = None

    for time, is_down in sorted(pedal):
        if is_down and down_time is None:
            down_time = time
        elif not is_down and down_time is not None:
            intervals.append((down_time, time))
            down_time = None

    if down_time is not None:
        intervals.append((down_time, end))

    return intervals

"""
Makes notes released while the pedal is down keep sounding until the pedal comes up

Args:
    notes (list): Note dictionaries from audioproc.extract_notes()
    pedal (list): (time, is_down) tuples from audioproc.extract_pedal()

Returns:
    list: new note dictionaries with longer durations where the pedal held them
"""
def apply_pedal(notes, pedal):
    end = max(note['start'] + note['duration'] for note in notes)
    intervals = pedal_intervals(pedal, end)

    held_notes = []
    for note in notes:
        released = note['start'] + note['duration']

        for down_time, up_time in intervals:
            if down_time <= released < up_time:
                note = {**note, 'duration': up_time - note['start']}
                break

        held_notes.append(note)

    return held_notes

"""
Renders every note into one audio buffer and saves it as a wav file

Args:
    samples (dict): The loaded samples from load_samples()
    notes (list): Note dictionaries from audioproc.extract_notes()
    out_path (string): Where to save the wav file
    pedal (list): (time, is_down) tuples from audioproc.extract_pedal(), if any
    progress (function): Called every 100 notes with the fraction done (0 to 1), if given
"""
# ponytail: linear scan of every pedal interval per note, bisect if rendering gets slow
def render_song(samples, notes, out_path, pedal=(), progress=None):
    notes = apply_pedal(notes, pedal)
    end = max(note['start'] + note['duration'] for note in notes) + RELEASE
    buffer = np.zeros((int(end * SAMPLE_RATE) + 2, 2), dtype=np.float32)

    for i, note in enumerate(notes):
        if progress and i % 100 == 0:
            progress(i / len(notes))

        audio = render_note(samples, note['pitch'], note['duration'], note['velocity'])
        offset = int(note['start'] * SAMPLE_RATE)
        buffer[offset:offset + len(audio)] += audio

    # overlapping notes add up, so turn the whole song down if it would clip
    peak = np.abs(buffer).max()
    if peak > 1:
        buffer /= peak

    with wave.open(out_path, "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes((buffer * 32767).astype(np.int16).tobytes())

# run `python render.py` to check the samples load correctly
if __name__ == "__main__":
    pygame.mixer.pre_init(SAMPLE_RATE, -16, 2)
    pygame.mixer.init()

    assert filename_to_pitch("A0.ogg") == 21
    assert filename_to_pitch("Ds1.ogg") == 27
    assert filename_to_pitch("C4.ogg") == 60
    assert filename_to_pitch("C8.ogg") == 108

    samples = load_samples()
    assert len(samples) == 30, f"expected 30 samples, got {len(samples)}"

    for pitch in sorted(samples):
        print(pitch, samples[pitch].shape)
    print("mixer:", pygame.mixer.get_init())

    # a 1 second middle C: held 1s, then the release tail
    note = render_note(samples, 60, 1.0)
    assert note.shape == (int((1.0 + RELEASE) * SAMPLE_RATE), 2)
    assert np.abs(note).max() > 0.01, "note is silent"
    assert np.abs(note[-1]).max() < 1e-3, "note doesn't fade to silence"

    # a pitch with no sample of its own gets shifted from a neighbor (61 -> from 60)
    shifted = render_note(samples, 61, 1.0)
    assert shifted.shape == note.shape
    assert not np.array_equal(shifted, note)

    # softer notes are quieter, and velocity 127 is the unscaled sample
    soft = render_note(samples, 60, 1.0, velocity=40)
    assert np.abs(soft).max() < np.abs(note).max()
    assert np.array_equal(render_note(samples, 60, 1.0, velocity=127), note)

    # a note held longer than its sample can't outlast the sample
    assert len(render_note(samples, 108, 100.0)) < len(samples[108])

    # a C major chord at 1s, then one more note at 3s
    import tempfile
    chord = [{'pitch': p, 'start': 1.0, 'duration': 1.0, 'velocity': 100} for p in (60, 64, 67)]
    chord.append({'pitch': 72, 'start': 3.0, 'duration': 0.5, 'velocity': 100})
    path = os.path.join(tempfile.mkdtemp(), "test.wav")
    render_song(samples, chord, path)

    with wave.open(path, "rb") as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (2, 2, SAMPLE_RATE)
        assert abs(wav.getnframes() - int((3.5 + RELEASE) * SAMPLE_RATE)) < 5
        audio = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16).reshape(-1, 2)

    assert np.array_equal(load_wav(path), audio)
    assert not audio[:SAMPLE_RATE - 100].any(), "should be silent before the first note"
    assert np.abs(audio[SAMPLE_RATE:2 * SAMPLE_RATE]).max() > 1000, "chord is silent"
    assert np.abs(audio[3 * SAMPLE_RATE:int(3.5 * SAMPLE_RATE)]).max() > 1000, "last note is silent"

    # pedal presses become (down, up) ranges, and a repeated press is ignored
    assert pedal_intervals([(1, True), (1.5, True), (2, False), (3, True)], end=5) == [(1, 2), (3, 5)]

    # a note released while the pedal is down rings until the pedal comes up
    held = [
        {'pitch': 60, 'start': 0.0, 'duration': 1.5, 'velocity': 100},  # released at 1.5, pedal down
        {'pitch': 62, 'start': 0.0, 'duration': 0.5, 'velocity': 100},  # released at 0.5, before the pedal
        {'pitch': 64, 'start': 2.0, 'duration': 0.5, 'velocity': 100},  # released at 2.5, after the pedal
    ]
    pedal = [(1.0, True), (2.0, False)]
    result = apply_pedal(held, pedal)
    assert [n['duration'] for n in result] == [2.0, 0.5, 0.5]
    assert held[0]['duration'] == 1.5, "apply_pedal changed the original notes"

    # the pedal makes the rendered song longer
    render_song(samples, [{'pitch': 60, 'start': 0.0, 'duration': 1.0, 'velocity': 100}], path, pedal=[(0.5, True), (3.0, False)])
    with wave.open(path, "rb") as wav:
        assert abs(wav.getnframes() - int((3.0 + RELEASE) * SAMPLE_RATE)) < 5

    # lots of loud overlapping notes get turned down instead of clipping
    pile = [{'pitch': 60, 'start': 0, 'duration': 1.0, 'velocity': 127} for _ in range(20)]
    render_song(samples, pile, path)
    with wave.open(path, "rb") as wav:
        loud = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)
    assert np.abs(loud.astype(np.int32)).max() <= 32767

    print("ok")
