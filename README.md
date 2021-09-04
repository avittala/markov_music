# Markov Music
Automatically generate music using Markov processes.
This project consists of two parts:
1. A flexible Music class capable of compiling note sequences to MIDI and playing this music.
2. Helper functions to create the note sequences via a Markov process

# The Music class:
Here's a quick look at sample usage of this class:
```
m = Music(120)
```
This generates a Music object with a tempo of 120 bpm. 
You can set a time signature (beats per measure, 4 = 4/4 time) and key signature (0 = C) by directly accessing the Music object.
```
m.ts = 4
m.key = 0
```
To add notes, use the `add_notes()` function. Remember that the `base_pitch` is automatically added to any pitch.
```
ns = [()]
m.add_notes(ns)



