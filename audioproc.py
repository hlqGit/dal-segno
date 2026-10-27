import mido

"""
Parses a midi file and returns a list of note events

Args: 
    filepath (string): The filepath of the midi note to parse
    save_path (string): The filepath of the midi with the start delay added
    start_delay (int): The amount of delay to add to the beginning in seconds

Returns:
    list: list of dictionaries containing pitch, start, duration, and velocity
"""
def extract_notes(filepath, save_path, start_delay):
    midi_file = mido.MidiFile(filepath)

    tempo = 500000 
    for track in midi_file.tracks:
        for msg in track:
            if msg.time > 0:
                break
            if msg.type == 'set_tempo':
                tempo = msg.tempo
                break
                
    delay_ticks = int(mido.second2tick(start_delay, midi_file.ticks_per_beat, tempo))

    for track in midi_file.tracks:
        if len(track) > 0:
            track[0].time += delay_ticks

    midi_file.save(save_path)

    parsed_notes = []
    active_notes = {}
    absolute_time = 0
    
    for msg in midi_file:
        absolute_time += msg.time

        # checking for a note-on event
        if msg.type == 'note_on' and msg.velocity > 0:
            active_notes[msg.note] = (absolute_time, msg.velocity)

        # checking for a note-off event
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            if msg.note in active_notes:
                start_time, velocity = active_notes.pop(msg.note)
                duration = absolute_time - start_time

                parsed_notes.append({
                    'pitch': msg.note,
                    'start': start_time,
                    'duration': duration,
                    'velocity': velocity
                })

    return parsed_notes

"""
Parses a midi file and returns the sustain pedal presses and releases

Args:
    filepath (string): The filepath of the midi file to parse
    start_delay (int): The same start delay given to extract_notes, in seconds

Returns:
    list: list of (time, is_down) tuples, in seconds
"""
def extract_pedal(filepath, start_delay):
    pedal_events = []
    absolute_time = start_delay

    for msg in mido.MidiFile(filepath):
        absolute_time += msg.time

        # control 64 is the sustain pedal, 64 and up means pressed
        if msg.type == 'control_change' and msg.control == 64:
            pedal_events.append((absolute_time, msg.value >= 64))

    return pedal_events