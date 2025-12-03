# server/audio/state.py

live_transcript = []


def get_live_transcript():
    return live_transcript


def add_to_transcript(entry):
    live_transcript.append(entry)

