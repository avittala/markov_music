from pydub import AudioSegment
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import sys
from music import Music

# run with a sample file
filename = 'sample.m4a'
if len(sys.argv) > 1:
	filename = sys.argv[1]
print(filename)


def audio_file_to_music(filename):
	# load audio and compute spectrogram 
	audio = AudioSegment.from_file(filename,format=filename[-3:])
	print('Width', audio.sample_width, 'Rate', audio.frame_rate, 'Channels', audio.channels, 'Duration',audio.duration_seconds)
	fr = audio.frame_rate
	a = audio.get_array_of_samples() # convert to raw audio wave
	type = a.typecode
	a = np.array(a).astype(float)
	a = a/np.iinfo(type).max # normalize audio waves

	# compute spectrogram
	f, t, Sxx = signal.spectrogram(a, fr, nperseg=8192)
	print('Frequency accuracy:',f[1]-f[0],'Hz')
	print('Min frequency for note identification:',(f[1]-f[0])/(2**(1/12)-1), 'Hz') # lowest freq note that can be identified
	print('Time accuracy:',t[1]-t[0],'s')
	# plt.pcolormesh(t, f[:150], Sxx[:150,:], shading='gouraud')
	# plt.ylabel('Frequency [Hz]')
	# plt.xlabel('Time [sec]')
	# plt.show()

	# find power in each note
	power, freqs = Sxx, f
	notes = np.zeros((13, power.shape[1])) # total power in each note over time
	freqs_to_notes = np.zeros_like(freqs).astype(int)
	# clipping range for notes, any frequency above or below is ignored
	low_f = (2**2)*27.5  # A2
	high_f = (2**8)*27.5 # A8
	for i in range(len(freqs)):
		if freqs[i] < low_f:
			freqs_to_notes[i] = 0 # too low to accurately classify
		elif freqs[i] > high_f:
			freqs_to_notes[i] = 0 # too high to keep
		else:
			freqs_to_notes[i] = np.round(np.log(freqs[i]/low_f)/np.log(2**(1/12)))%12 + 1 # A = 1, ..., G# = 13
	for j in range(power.shape[1]):
		for i in range(power.shape[0]):
			notes[freqs_to_notes[i], j] += power[i,j]
	notes =  notes[1:,:] # remove bottom row, which has too high or too low frequencies

	plt.imshow(notes, aspect='auto', origin='lower')
	plt.xticks(np.linspace(0,len(t),num=10,endpoint=False), np.round(t[::len(t)//10][:10],2))
	plt.xlabel('Time (s)')
	plt.ylabel('Pitch (from A = 0)')
	plt.show()

	return notes
	# threshold notes
	# calculate most common duration and use to determine BPM
	# convert notes to a music object afterwards

music = audio_file_to_music(filename)

