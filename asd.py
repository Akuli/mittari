import os
import io
import wave


SAMPLE_RATE = 44100
DURATION = 2
FREQUENCY = 1000

def square_wave(x, duty_cycle):
    if x % 1 < duty_cycle:
        return 1
    else:
        return -1

def two_monos_to_stereo(left: bytes, right: bytes) -> bytes:
    assert len(left) == len(right)
    return b"".join(left[i:i+2] + right[i:i+2] for i in range(0, len(left), 2))
    

def play(duty_cycle):
    left_channel_data = b"".join(
        round(
            square_wave(FREQUENCY*i/SAMPLE_RATE, duty_cycle) * 0x7fff
        ).to_bytes(2, byteorder='little', signed=True)
        for i in range(round(DURATION * SAMPLE_RATE))
    )

    right_channel_data = b"".join(
        round(
            square_wave(FREQUENCY*i/SAMPLE_RATE, duty_cycle) * 0x7fff
        ).to_bytes(2, byteorder='little', signed=True)
        for i in range(round(DURATION * SAMPLE_RATE))
    )


    f = io.BytesIO()
    with wave.open(f, 'w') as wav:
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.setnchannels(2)
        wav.writeframes(two_monos_to_stereo(left_channel_data, right_channel_data))

    with open('/tmp/a.wav', 'wb') as file:
        file.write(f.getvalue())

    # desktop
    #os.system("cd /tmp && aplay -D front:CARD=PCH,DEV=0 a.wav")

    # laptop
    os.system("cd /tmp && aplay -D front:CARD=Intel,DEV=0 a.wav")


duty_cycle = 0
while duty_cycle < 1:
    print(round(duty_cycle, 10))
    play(1-duty_cycle)  # laptop needs inverting?
    duty_cycle += 0.001
