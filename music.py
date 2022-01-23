import time

class Music():
	"""
	A class used to hold Music
	
	Attributes
	----------
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
	"""
	# Initialize a music object
	def __init__(self):
		self.tempo = 120
		self.timestep = 60/self.tempo # seconds per beat
		self.base_pitch = 60 # MIDI number to add to any pitch
		self.num_seq = 0 # number of note sequences, maximum is 16!
		self.ts = 4 # time signature
		self.notes = [] # list of notes as tuples of (sequence number, pitch, beat on, beat off)
		self.program = [] # list of instructions (on and off and sleep) + their time stamps; create at end
		self.key = 0 # key to use
		self.instruments = []
		self.instr_dict = {'piano':(0,0), 'organ':(0,13),'violin':(1,26),
		'cello':(1,28), 'trumpet':(1,30), 'tuba':(1,32), 'oboe':(1,33), 'sax':(1,34), 
		'flute':(1,36), 'timpani':(1,38), 'guitar':(2,42)}
	# Add a note sequence (array of 3-tuples (pitch, offset in beats, duration in beats)) to the Music
	def add_notes(self, ns, instrument='piano'):
		if self.num_seq == 16: # can't add more than 16 sequences
			raise BaseException('Too many note sequences!')
		beat = 0.0
		for p,off,d in ns:
			beat += off
			self.notes.append((self.num_seq, p, beat, beat+d))
			beat += d
		self.num_seq += 1 # move to next channel
		self.instruments.append(instrument) # add instrument
	# Compile program (turn into program and add in sleeps)
	def compile(self):
		self.program = []
		for seq, p, start, end in self.notes:
			self.program.append((start, 'on', seq, p+self.base_pitch)) # add 'on'
			self.program.append((end, 'off', seq, p+self.base_pitch)) # add 'off'
		self.program.sort() # sort program by time
		new_program = []
		time = 0.0
		for i in range(len(self.program)):
			prog = self.program[i]
			new_program.append((time, 'sleep', prog[0]-time)) # add in a sleep until the start, in beats
			new_program.append(prog) # add in the instruction
			time = prog[0]
		self.program = new_program
		print('Total music time:',time,'seconds')
	# Play the Music, requires fluidsynth and the pyfluidsynth library to be installed
	def play(self):
		import fluidsynth
		self.compile() # compile program
		fs = fluidsynth.Synth(gain=0.2) # load and start synthesizer
		fs.start()
		sfid = fs.sfload("Essential Keys-sfzBanks-v9.6.sf2") # load instruments
		for i in range(self.num_seq):
			instr = self.instr_dict[self.instruments[i]]
			fs.program_select(i, sfid, instr[0], instr[1])
		for p in self.program: # run program
			if p[1] == 'on':
				fs.noteon(p[2], p[3], 120)
			elif p[1] == 'off':
				fs.noteoff(p[2], p[3])
			elif p[1] == 'sleep':
				time.sleep(p[2]*self.timestep)
		fs.delete()
	# Write Music to a MIDI file
	def write(self, name):
		# quick function to convert an integer into a bytearray, length specifies total length in bytes (left pad with zeroes)
		def num_to_bytes(num, base=10, length=0):
			hex_string = hex(int(str(num), base=base))[2:]
			hex_string = '0'*(length*2-len(hex_string)) + hex_string
			return bytearray.fromhex(hex_string)
		# quick function to convert a decimal to a variable-length quantity
		def decimal_to_vlq(num):
			bin_string = bin(num)[2:] # turn to binary
			bin_string = '0'*((-len(bin_string))%7)+bin_string # add zeros at start
			hex_vals = [bin_string[i*7:i*7+7] for i in range(len(bin_string)//7)] 
			bin_7_string = ""
			for i in range(len(hex_vals)):
					if i >= len(hex_vals)-1:
							bin_7_string += '0'+hex_vals[i]
					else:
							bin_7_string += '1'+hex_vals[i]
			return num_to_bytes(bin_7_string, base=2, length=len(hex_vals))
		self.compile() # turn into a good program to use
		header_chunk = bytearray(b"MThd") # header chunk (4 bytes)
		header_chunk += b"\x00\x00\x00\x06" # length of header chunk (4 bytes)
		header_chunk += b"\x00\x00" # format of file (single track, 2 bytes)
		header_chunk += b"\x00\x01" # add number of tracks to header (one track, 2 bytes)
		header_chunk += b"\x00\x60" # divisions, 96 ticks per beat (2 bytes)
		track_chunk_header = bytearray(b"MTrk") # start of track chunk (4 bytes)
		track_chunk = bytearray()
		track_chunk += b'\x00\xff\x58\x04' + num_to_bytes(self.ts, length=1) + b'\x02\x24\x08' # add time signature
		track_chunk += b'\x00\xff\x51\x03' + num_to_bytes(round(self.timestep*1000000), length=3) # add tempo
		for j in range(len(self.program)):
			if len(self.program[j]) == 4:
				t_stamp, instr, seq, pitch = self.program[j]
			else:
				t_stamp, instr, time = self.program[j]
			if instr == 'sleep':
				track_chunk += decimal_to_vlq(round(time*96))
			elif instr == 'on':
				track_chunk += num_to_bytes(9*16+seq, length=1) + num_to_bytes(pitch, length=1)+b'\x40'
			elif instr == 'off':
				track_chunk += num_to_bytes(8*16+seq, length=1) + num_to_bytes(pitch, length=1)+b'\x40'
		track_chunk += b'\x00\xff\x2f\x00' # end track
		track_len = len(track_chunk)
		track_chunk_header += num_to_bytes(track_len, length=4) # add length of chunk
		# write file
		file = open(name, 'wb')
		midi = header_chunk + track_chunk_header + track_chunk
		file.write(midi)
		file.close()