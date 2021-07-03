# Generate music using a simple Markov process
# Ensure harmony/not much dissonance as well for multiple lines
from music import Music
import random

# factors denote how much more likely a note ...
in_key_factor = 10 # is in the key
is_close_factor = 10 # is close (a Maj 3rd) to previous note
is_diff_factor = 5 # is different than the previous note
is_match_factor = 100 # harmonizes with the concurrent notes (unison, 3rd, 6th)
is_spaced_factor = 10 # is spaced out from concurrent notes (a Maj 3rd away)
in_meas_factor = 100 # ends within the measure
on_beat_factor = 10 # note ends or starts on beat (i.e. on a quarter note)

repeat_start_chance = 0.5 # how often we start repeats (per measure)
repeat_end_chance = 0.4 # how often we end repeats (per measure)

# create melody
# m is the Music object, num is number of measures, ts is time signature
def make_melody(music, num_m,  ts=4, key=0, instr='piano', durs=[1,2,3,4], dur_to_beat = 4, p_range=(0,12)):
	music.ts = ts # set time signature
	music.key = key # set key
	cur_m = 0 # current measure
	rem_dur = dur_to_beat*ts # remaining duration in measure (durs per beat times beats per measure)
	ns = [] # notes
	# choose pitch within two octaves
	p_trans = [j for j in range(p_range[0],p_range[1]+1)] # range of pitches allowed
	p = -542 # curr pitch
	# choose duration
	d_trans = durs
	while cur_m < num_m:
		# set pitch distribution
		p_probs = [0]*len(p_trans)
		d_probs = [0]*len(d_trans)
		for i in range(len(p_trans)):
			p_next = p_trans[i]
			in_key = (p_next - key)%12 in (0,2,4,5,7,9,11) # check if it's in the key
			is_close = abs(p_next-p) < 5 # check if within a maj3rd
			is_diff = (p_next != p) # check if melody changed
			p_probs[i] = 1.0*(in_key_factor*in_key+1)*(is_close_factor*is_close+1)*(is_diff_factor*is_diff+1)
		p_probs = [prob/sum(p_probs) for prob in p_probs] # normalize
		for i in range(len(d_trans)):
			in_meas = (d_trans[i] <= rem_dur) # check if within measure
			on_beat = ((rem_dur - d_trans[i])%dur_to_beat == 0) or rem_dur%dur_to_beat == 0 # check if ends or starts on beat
			d_probs[i] = 1.0*(in_meas_factor*in_meas+1)*(on_beat_factor*on_beat+1) 
		d_probs = [prob/sum(d_probs) for prob in d_probs] # normalize
		# choose pitch from distribution
		p = random.choices(p_trans, weights=p_probs)[0]
		# choose duration from distribution
		d = random.choices(d_trans, weights=d_probs)[0]
		rem_dur -= d
		if rem_dur <= 0:
			rem_dur = dur_to_beat*ts
			cur_m += 1
		ns.append((p,0,d/dur_to_beat)) # add note and duration
	music.add_notes(ns, instrument=instr)

# give start and end beats, find indices of all overlapping notes with another interval
def get_overlaps(music, start, end):
	notes = music.notes
	indices = []
	for i in range(len(notes)):
		n_start, n_end = notes[i][2], notes[i][3] # extract start and end beat of note
		# if end of note is after the start AND start of note is before the end
		if n_end >= start and n_start <= end: 
			indices.append(i) # add note
	return indices

# find harmony given music object and starting note
def add_harmony(music, instr='piano', durs=[1,2,3,4], dur_to_beat = 4, p_range=(-12,0)):
	ts = music.ts
	key = music.key
	end_of_notes = max([n[3] for n in music.notes]) # last beat of piece
	hns = [] # array to hold notes
	hp_trans = [j for j in range(p_range[0],p_range[1]+1)] # range of pitches allowed
	hp = -542 # curr pitch
	rem_dur = dur_to_beat*ts # remaining duration in measure
	# choose duration (4 durs is one beat)
	hd_trans = durs
	beats = 0.0
	while beats < end_of_notes:
		# we want to use this note
		hd_probs = [0]*len(hd_trans)
		for i in range(len(hd_trans)):
			in_meas = (hd_trans[i] <= rem_dur) # check if within measure
			on_beat = ((rem_dur - hd_trans[i])%dur_to_beat == 0) or rem_dur%dur_to_beat == 0 # check if ends or starts on a beat
			hd_probs[i] = 1.0*(in_meas_factor*in_meas+1)*(on_beat_factor*on_beat+1)
		hd_probs = [prob/sum(hd_probs) for prob in hd_probs] # normalize
		# choose duration from distribution
		hd = random.choices(hd_trans, weights=hd_probs)[0]
		rem_dur -= hd
		if rem_dur <= 0:
			rem_dur = dur_to_beat*ts
		indices = get_overlaps(music, beats, beats+hd) # find overlapping notes from music object
		ps = [music.notes[i][1] for i in indices] # find their pitches
		hp_probs = [0]*len(hp_trans)
		for j in range(len(hp_trans)): # calculate probabilities
			hp_next = hp_trans[j]
			in_key = (hp_next - key)%12 in (0,2,4,5,7,9,11) # check if it's in the key
			is_match = 0.0 # check if harmonizes with melody (unison, 3rd, or 6th)
			is_spaced = 0.0 # check if at least a 3rd from other notes
			for p in ps: 
				is_match += 1.0*((hp_next - p)%12 in (0,3,4,8,9))/len(ps) # average number it matches
				is_spaced += 1.0*(abs(hp_next - p) > 5)/len(ps) # check if harmony is far enough from melody
			is_close = abs(hp_next-hp) < 5 # check if change is within a maj3rd
			is_diff = (hp_next != hp) # check if note changed
			hp_probs[j] = 1.0*(in_key_factor*in_key+1)*(is_close_factor*is_close+1)*(is_match_factor*is_match+1)*(is_spaced_factor*is_spaced+1)*(is_diff_factor*is_diff+1)
		hp_probs = [prob/sum(hp_probs) for prob in hp_probs] # normalize
		# choose pitch from distribution
		hp = random.choices(hp_trans, weights=hp_probs)[0]
		hns.append((hp,0,hd/dur_to_beat)) # add note
		beats += hd/dur_to_beat # move to next harmony note
	music.add_notes(hns, instrument=instr)

# make delayed copy of notes
def delayed_copy(notes, delay):
	delayed_notes = []
	for n in notes:
		delayed_notes.append((n[0],n[1],n[2]+delay,n[3]+delay))
	return delayed_notes

# add repetitions to music, stochastically and recursively
def add_repetitions(music):
	music.notes.sort(key=lambda n: n[2]) # sort notes by start beat
	ts = music.ts
	# generate starts and ends of measures
	measures = []
	i = 0
	while i < len(music.notes):
		start = i
		beat_on = music.notes[i][2]
		while i < len(music.notes) and (music.notes[i][2] - beat_on < ts):
			i += 1
		end = i-1
		if (music.notes[end][3] - beat_on) >= ts-0.1: # only add a measure if it's long enough
			measures.append((start,end))
	# generate positions of starts and ends of repeats
	print(measures)
	starts = []
	ends = []
	for m in measures:
		if random.random() < repeat_start_chance:
			starts.append(m[0])
		if len(starts) > len(ends) and random.random() < repeat_end_chance:
			ends.append(m[1])
	for j in range(len(starts)-len(ends)): # add any left over ends
		ends.append(len(music.notes)-1)
	print(starts, ends)
	# add in repeats
	for j in range(len(starts)-1, -1, -1):
		s = starts[j]
		e = None
		for k in range(len(ends)): # choose the end that is closest to this start
			if ends[k] > s:
				e = ends[k] # choose this end
				ends[k] = -1 # remove since we've used this end
				break
		delay_num_measures = round((music.notes[e][2] - music.notes[s][2])/ts) # delay time is on of start note to off of end note
		len_delay = delay_num_measures*ts # convert to delay in beats
		music.notes = music.notes[:e+1]+delayed_copy(music.notes[s:], len_delay) # repeat in the notes 
		# fix indices in ends (no adjustments needed to starts as we go backward from end)
		for k in range(len(ends)):
			if ends[k] >= e:
				ends[k] += len(music.notes[s:e+1]) # adjust by how many notes we've added

# add repetitions (simple, not complex)
def add_repetitions_simple(music):
	music.notes.sort(key=lambda n: n[2]) # sort notes by start beat
	ts = music.ts
	# generate starts and ends of measures
	measures = []
	i = 0
	while i < len(music.notes):
		start = i
		beat_on = music.notes[i][2]
		while i < len(music.notes) and (music.notes[i][2] - beat_on < ts):
			i += 1
		end = i-1
		if (music.notes[end][3] - beat_on) >= ts-0.1: # only add a measure if it's long enough
			measures.append((start,end))
	# generate positions of starts and ends of repeats
	print(measures)
	starts = []
	ends = []
	for m in measures:
		if len(ends) == len(starts) and random.random() < repeat_start_chance:
			starts.append(m[0])
		if len(starts) > len(ends) and random.random() < repeat_end_chance:
			ends.append(m[1])
	for j in range(len(starts)-len(ends)): # add any left over ends
		ends.append(len(music.notes)-1)
	print(starts, ends)
	# add in repeats
	for j in range(len(starts)-1, -1, -1):
		s = starts[j]
		e = None
		for k in range(len(ends)): # choose the end that is closest to this start
			if ends[k] > s:
				e = ends[k] # choose this end
				ends[k] = -1 # remove since we've used this end
				break
		delay_num_measures = round((music.notes[e][2] - music.notes[s][2])/ts) # delay time is on of start note to off of end note
		len_delay = delay_num_measures*ts # convert to delay in beats
		music.notes = music.notes[:e+1]+delayed_copy(music.notes[s:], len_delay) # repeat in the notes 
		# fix indices in ends (no adjustments needed to starts as we go backward from end)
		for k in range(len(ends)):
			if ends[k] >= e:
				ends[k] += len(music.notes[s:e+1]) # adjust by how many notes we've added

# np.random.seed(0)
m = Music(120)
key = random.randint(0,11)
make_melody(m, 10, ts=4, key=0, instr='piano', durs=[1,2,3,4], dur_to_beat = 4, p_range=(6,18)) # make melody from Markov process
# add_harmony(m, instr='piano', durs=[2,4,8], dur_to_beat = 4, p_range=(-6,6)) # add in a harmony line
add_repetitions(m)
add_harmony(m, instr='piano', durs=[2,4,8], dur_to_beat = 4, p_range=(-18,-6)) # add in a harmony line
m.compile() # turn into a program that can be played
m.write('out.midi') # write music
m.play() # play the music



