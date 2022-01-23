# Generate music using a simple Markov process
# Ensure harmony/not much dissonance as well for multiple lines
from music import Music
import random

# a Markov process-generated Music
class MarkovMusic(Music):
	"""
	A class used to hold Markov process-generated Music
	
	Attributes
	----------
	-- Inherited from class Music -- 
	tempo: float
		beats per minute for music
	timestep: float
		seconds per beat
	base_pitch: int
		base value to add to pitches of notes
		C5 = 60, C#5/Db5 = 61, etc.
	num_seq: int
		number of note sequences added in
	ts: int
		time signature, beats per measure
	notes: list of 4-tuples
		list notes as (sequence number, pitch, beat on, beat off)
	program: list of 2 or 4 tuple instructions
		list of note on/off (instruction time, instruction, sequence number, true pitch)
		and sleep events (instruction time, instruction, sleep time)
	key: int, 0-11 inclusive
		key signature, 0 = C, 1 = C#/Db, etc.
	instruments: list
		instrument to use from instr_dict for each note sequence
	instr_dict: dict
		maps instrument name to tuple of bank number and ID in sf2 file
	-- New attributes -- 
	in_key_factor: float
		how much more likely is a note given it is in the key
	is_close_factor: float
		how much more likely is a note given it is close (a Maj 3rd) to previous note
	is_diff_factor: float
		how much more likely is a note given it iis different than the previous note
	is_match_factor: float
		how much more likely is a note given it harmonizes with the concurrent notes (unison, 3rd, 6th)
	is_spaced_factor: float
		how much more likely is a note given it is spaced out from concurrent notes (a Maj 3rd away)
	in_meas_factor: float
		how much more likely is a duration given it ends within the measure
	on_beat_factor: float
		how much more likely is a duration given it ends or starts on beat (i.e. on a quarter note)
	repeat_start_chance: float
		how often we start repeats (per measure)
	repeat_end_chance: float
		how often we end repeats (per measure)
	"""
	def __init__(self):
		Music.__init__(self)
		# factors denote how much more likely a note ...
		self.in_key_factor = 10 # is in the key
		self.is_close_factor = 10 # is close (a Maj 3rd) to previous note
		self.is_diff_factor = 5 # is different than the previous note
		self.is_match_factor = 100 # harmonizes with the concurrent notes (unison, 3rd, 6th)
		self.is_spaced_factor = 10 # is spaced out from concurrent notes (a Maj 3rd away)
		self.in_meas_factor = 100 # ends within the measure
		self.on_beat_factor = 10 # ends or starts on beat (i.e. on a quarter note)
		self.repeat_start_chance = 0.5 # how often we start repeats (per measure)
		self.repeat_end_chance = 0.4 # how often we end repeats (per measure)

	# create melody
	# num_m is number of measures, ts is time signature
	# durs are allowable note durations in parts of a beat, dur_to_beat indicates how many parts to a beat
	# p_range is the range of pitches allowed relative to the MarkovMusic's base_pitch
	def make_melody(self, num_m,  ts=4, key=0, instr='piano', durs=[1,2,3,4], dur_to_beat = 4, p_range=(0,12)):
		self.ts = ts # set time signature
		self.key = key # set key
		cur_m = 0 # current measure
		rem_dur = dur_to_beat*self.ts # remaining duration within measure (durs per beat times beats per measure)
		ns = [] # notes
		# choose pitch within two octaves
		p_trans = [j for j in range(p_range[0],p_range[1]+1)] # range of pitches allowed
		p = -542 # curr pitch, this value is arbitrary
		# choose duration
		d_trans = durs
		while cur_m < num_m:
			# set pitch distribution
			p_probs = [0]*len(p_trans)
			d_probs = [0]*len(d_trans)
			for i in range(len(p_trans)):
				p_next = p_trans[i]
				in_key = (p_next - self.key)%12 in (0,2,4,5,7,9,11) # check if it's in the key
				is_close = abs(p_next-p) < 5 # check if within a maj3rd
				is_diff = (p_next != p) # check if melody changed
				p_probs[i] = 1.0*(self.in_key_factor*in_key+1)*(self.is_close_factor*is_close+1)*(self.is_diff_factor*is_diff+1)
			p_probs = [prob/sum(p_probs) for prob in p_probs] # normalize
			for i in range(len(d_trans)):
				in_meas = (d_trans[i] <= rem_dur) # check if within measure
				on_beat = ((rem_dur - d_trans[i])%dur_to_beat == 0) or rem_dur%dur_to_beat == 0 # check if ends or starts on beat
				d_probs[i] = 1.0*(self.in_meas_factor*in_meas+1)*(self.on_beat_factor*on_beat+1) 
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
		self.add_notes(ns, instrument=instr)

	# give start and end beats, find indices of all overlapping notes with another interval
	def get_overlaps(self, start, end):
		indices = []
		for i in range(len(self.notes)):
			n_start, n_end = self.notes[i][2], self.notes[i][3] # extract start and end beat of note
			# if end of note is after the start AND start of note is before the end
			if n_end >= start and n_start <= end: 
				indices.append(i) # add note
		return indices

	# find harmony given music object and starting note
	def add_harmony(self, instr='piano', durs=[1,2,3,4], dur_to_beat = 4, p_range=(-12,0)):
		end_of_notes = max([n[3] for n in self.notes]) # last beat of piece
		hns = [] # array to hold notes
		hp_trans = [j for j in range(p_range[0],p_range[1]+1)] # range of pitches allowed
		hp = -542 # curr pitch
		rem_dur = dur_to_beat*self.ts # remaining duration within measure
		# choose duration
		hd_trans = durs
		beats = 0.0
		while beats < end_of_notes:
			# we want to use this note
			hd_probs = [0]*len(hd_trans)
			for i in range(len(hd_trans)):
				in_meas = (hd_trans[i] <= rem_dur) # check if within measure
				on_beat = ((rem_dur - hd_trans[i])%dur_to_beat == 0) or rem_dur%dur_to_beat == 0 # check if ends or starts on a beat
				hd_probs[i] = 1.0*(self.in_meas_factor*in_meas+1)*(self.on_beat_factor*on_beat+1)
			hd_probs = [prob/sum(hd_probs) for prob in hd_probs] # normalize
			# choose duration from distribution
			hd = random.choices(hd_trans, weights=hd_probs)[0]
			rem_dur -= hd
			if rem_dur <= 0:
				rem_dur = dur_to_beat*self.ts
			indices = self.get_overlaps(beats, beats+hd) # find overlapping notes
			ps = [self.notes[i][1] for i in indices] # find their pitches
			hp_probs = [0]*len(hp_trans)
			for j in range(len(hp_trans)): # calculate probabilities
				hp_next = hp_trans[j]
				in_key = (hp_next - self.key)%12 in (0,2,4,5,7,9,11) # check if it's in the key
				is_match = 0.0 # check if harmonizes with melody (unison, 3rd, or 6th)
				is_spaced = 0.0 # check if at least a 3rd from other notes
				for p in ps: 
					is_match += 1.0*((hp_next - p)%12 in (0,3,4,8,9))/len(ps) # average number it matches
					is_spaced += 1.0*(abs(hp_next - p) > 5)/len(ps) # check if harmony is far enough from melody
				is_close = abs(hp_next-hp) < 5 # check if change is within a maj3rd
				is_diff = (hp_next != hp) # check if note changed
				hp_probs[j] = 1.0*(self.in_key_factor*in_key+1)*(self.is_close_factor*is_close+1)*(self.is_match_factor*is_match+1)*(self.is_spaced_factor*is_spaced+1)*(self.is_diff_factor*is_diff+1)
			hp_probs = [prob/sum(hp_probs) for prob in hp_probs] # normalize
			# choose pitch from distribution
			hp = random.choices(hp_trans, weights=hp_probs)[0]
			hns.append((hp,0,hd/dur_to_beat)) # add note
			beats += hd/dur_to_beat # move to next harmony note
		self.add_notes(hns, instrument=instr)

	# make delayed copy of notes
	def delayed_copy(self, notes, delay):
		delayed_notes = []
		for n in notes:
			delayed_notes.append((n[0],n[1],n[2]+delay,n[3]+delay))
		return delayed_notes

	# add repetitions to music, stochastically and recursively
	def add_repetitions(self):
		self.notes.sort(key=lambda n: n[2]) # sort notes by start beat
		# generate starts and ends of measures
		measures = []
		i = 0
		while i < len(self.notes):
			start = i
			beat_on = self.notes[i][2]
			while i < len(self.notes) and (self.notes[i][2] - beat_on < self.ts):
				i += 1
			end = i-1
			if (self.notes[end][3] - beat_on) >= self.ts-0.1: # only add a measure if it's long enough
				measures.append((start,end))
		# generate positions of starts and ends of repeats
		print(measures)
		starts = []
		ends = []
		for m in measures:
			if random.random() < self.repeat_start_chance:
				starts.append(m[0])
			if len(starts) > len(ends) and random.random() < self.repeat_end_chance:
				ends.append(m[1])
		for j in range(len(starts)-len(ends)): # add any left over ends
			ends.append(len(self.notes)-1)
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
			delay_num_measures = round((self.notes[e][2] - self.notes[s][2])/self.ts) # delay time is on of start note to off of end note
			len_delay = delay_num_measures*self.ts # convert to delay in beats
			self.notes = self.notes[:e+1]+self.delayed_copy(self.notes[s:], len_delay) # repeat in the notes 
			# fix indices in ends (no adjustments needed to starts as we go backward from end)
			for k in range(len(ends)):
				if ends[k] >= e:
					ends[k] += len(self.notes[s:e+1]) # adjust by how many notes we've added

	# add repetitions (simple, not complex)
	def add_repetitions_simple(self):
		self.notes.sort(key=lambda n: n[2]) # sort notes by start beat
		# generate starts and ends of measures
		measures = []
		i = 0
		while i < len(self.notes):
			start = i
			beat_on = self.notes[i][2]
			while i < len(self.notes) and (self.notes[i][2] - beat_on < ts):
				i += 1
			end = i-1
			if (self.notes[end][3] - beat_on) >= ts-0.1: # only add a measure if it's long enough
				measures.append((start,end))
		# generate positions of starts and ends of repeats
		print(measures)
		starts = []
		ends = []
		for m in measures:
			if len(ends) == len(starts) and random.random() < self.repeat_start_chance:
				starts.append(m[0])
			if len(starts) > len(ends) and random.random() < self.repeat_end_chance:
				ends.append(m[1])
		for j in range(len(starts)-len(ends)): # add any left over ends
			ends.append(len(self.notes)-1)
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
			delay_num_measures = round((self.notes[e][2] - self.notes[s][2])/self.ts) # delay time is on of start note to off of end note
			len_delay = delay_num_measures*self.ts # convert to delay in beats
			self.notes = self.notes[:e+1]+delayed_copy(self.notes[s:], len_delay) # repeat in the notes 
			# fix indices in ends (no adjustments needed to starts as we go backward from end)
			for k in range(len(ends)):
				if ends[k] >= e:
					ends[k] += len(self.notes[s:e+1]) # adjust by how many notes we've added


