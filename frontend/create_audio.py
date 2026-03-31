import struct
import os

def create_silent_wav(filename, duration=1.0, sample_rate=44100):
    """Create a silent WAV file"""
    num_samples = int(duration * sample_rate)
    
    # WAV file header
    byte_rate = sample_rate * 2  # 2 bytes per sample (16-bit mono)
    wav_data = b'RIFF'
    wav_data += struct.pack('<I', 36 + num_samples * 2)  # File size - 8
    wav_data += b'WAVE'
    wav_data += b'fmt '
    wav_data += struct.pack('<I', 16)  # Subchunk1Size
    wav_data += struct.pack('<H', 1)   # AudioFormat (1 = PCM)
    wav_data += struct.pack('<H', 1)   # NumChannels (1 = mono)
    wav_data += struct.pack('<I', sample_rate)  # SampleRate
    wav_data += struct.pack('<I', byte_rate)    # ByteRate
    wav_data += struct.pack('<H', 2)   # BlockAlign
    wav_data += struct.pack('<H', 16)  # BitsPerSample
    wav_data += b'data'
    wav_data += struct.pack('<I', num_samples * 2)  # Subchunk2Size
    
    # Silent audio data (zeros)
    wav_data += b'\x00' * (num_samples * 2)
    
    with open(filename, 'wb') as f:
        f.write(wav_data)
    print(f'Created {filename}')

# Create filler audio files
for i in range(1, 4):
    create_silent_wav(f'filler{i}.wav', duration=0.5)
