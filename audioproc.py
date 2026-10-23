import mido

"""
Parses a midi file and returns a list of note events

Args: 
    filepath (string): The filepath of the midi note to parse

Returns:
    list: list of dictionaries containing pitch, start, and duration
"""
def extract_notes(filepath):
    midi_file = mido.MidiFile(filepath)
    parsed_notes = []

    active_notes = {}

    absolute_time = 0

    for msg in midi_file:
        absolute_time += msg.time

        # checking for a note-on event
        if msg.type == 'note_on' and msg.velocity > 0:
            active_notes[msg.note] = absolute_time

        # checking for a note-off event
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            if msg.note in active_notes:
                start_time = active_notes.pop(msg.note)
                duration = absolute_time - start_time

                parsed_notes.append({
                    'pitch': msg.note,
                    'start': start_time,
                    'duration': duration
                })

    return parsed_notes