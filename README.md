# Mittari

This electronics project is an analog CPU and RAM usage meter for my computer.
The idea is taken from [this youtube video](https://www.youtube.com/watch?v=4J-DTbZlJ5I).

TODO: picture of device outside

TODO: picture of device inside

The meters are controlled by sending audio out through the headphones jack.
This turned out to be the most convenient way to get a usable signal out of my computer.
Also, because the headphones jack supports stereo,
I conveniently get two channels (left and right) that I can use for the two meters.
This does mean that if I connect my headphones to the wrong place,
I will hear 1kHz beeping.

The actual meters are [this product from AliExpress](https://www.aliexpress.com/item/1005004735059319.html).
I used the 5mA version.


## Circuit Design

I designed an analog circuit to drive the meters and LEDs,
because I haven't yet learned to throw a microcontroller at every electronics problem.
Here is **one half** of the circuit, enough to drive one meter.
The other half is similar.

![circuit diagram](circuit.png)

[Click here to open the circuit in CircuitJS.](https://www.falstad.com/circuit/circuitjs.html?ctz=CQAgjCAMB0l3BWEB2aA2MBOZAOBaFkAmbSQkBSCkAFgGYKBTAWjDACgAlEZuo8ZGh5oaAoVQhh4UWHRpIqi6AnYBjHnzHghYQVHCx4R43DAtkPGPDSZItsHWR06aRy4WGOAJ21awQoiJRKnx4dgBzX0DRfxAgxSh2AEMQEW0JGhi0KhxaaGDwExlIOhKcZGIaIhsRBAdLWCD5PDAabHlIHDoEBikjdgB3VJi9WN1xdh80zB1MkBn9MBx+qdEFqnXwZcgI-U22fkVB4fA56Ymh1rWdTH519gATdOesfn8qfgfGADMkgFcADYAFzU4FuL3B0UW5hAdFgNneYDqRDkSNwxUgHEirziQTB-Hi+h2l3B73x8wu5LJRHwzx2QLitJpQlKomZix4YGgmFKXUwOBo5QIAsCMlcIjkPTgmBoaC6QkoVC+v0BIO4rLiNCoGpxCS11ASMBUPg1RGIsMgoj4CUV7Ec2stsKIDqtcvARN2GpcuS9Ao9Q3Z1KZtOJjJ02VhCDeEaIXFommW8f4mj1ISJMhUDJoYwjsqyCQgzBg9BlMzQBFciuzYrlaCIOEw-KWkCCbAocBAyv+wPY-n4UdyiYH4DABM7P27QOYAMYTwgMHExQ4DJEEgjw7JEgaeEgTgcSKCCAQbVyRtsLf5RFeyFlOH7Ha7quOea0bR0elDb60G4-k1oC3Gf8An1CRnV2L9CQgkNEiGF9Ey-RNPwWId6xARC-2zcNtSjOk0OdHY+woCMhwjA44nHFVgWnWd3QXIlYA4QiEHBIdSVHcjHyomc5zFejMWODd2NCEdDgE0ihLY0ShmY-gSJyI5pOIkJUPQ6TUKuCh1PYgi61oNJ4LSMjPgnVVqJ4w0GN7XT6FkqgbJEjiTK4mj5z4jhYITOz9IUpMHJfMjP0M9j-LmUMZLQqhVwixIfDJOK5k3Qo4D-KLEyixKkTCVY10i-VnVPLYwkiKL8uGD48SOAAPWgzgYOULHLWhwCQIgADUAB0AGdOr+AAHRgvC6gAjLwAEtwgACyBLqvFnLqkgAOweLqAE9GABAEAHsBi6gAZABRAARTr2Gqgg4kgHRSguzAmqREAAFUAEFkH5AAVABhU6LRa49YQwRkLBiJAACEPuPTAvuq7M3gbPTchxYGQDBiGoc0mI4YQRNEea5HwbaL7Nv0ArRxIbV8hwfwqkoGUbF3RqrFMfQFFhU5WdFcrYXYImsDQxZun8W7GcxJcSmwUpnDIHldIgN5broO0CoAMVcpQyE5EBWs24EknCRh2CAA)

At a high-level, my circuit:
- removes any DC offset from the headphones signal (this seems to be unnecessary, but doesn't hurt)
- clamps the input voltage between +-0.7V using diodes
- amplifies the input by 100x and stores the amplified max voltage into a capacitor
- uses a transistor connected as a voltage follower to drive the AliExpress current meter
- uses transistors to drive red or yellow LEDs (or both),
    depending on whether we are showing a value near 100%,
    using [this transistor trick](https://electronics.stackexchange.com/q/164068).

I used 1N4148 diodes, BC549C transistors and a UA798TC dual op-amp,
because I already had them.

The op-amp's output must go near the ground.
With no input signal, my dual op-amp charges the 100nF capacitor to 270mV on one side and 400mV on the other side.
More than a diode drop (about 600mV) would be bad,
because the transistor that drives the current meter would never turn off,
so it would be impossible to make the meter go to zero.

The UA798TC doesn't swing all the way to +5V, but it doesn't matter.
For example, at 3.7V, the meter will surely hit its maximum,
because even with a 0.7V diode drop in the transistor's base-emitter junction,
we would get `3V / 470ohm ≈ 6.3mA` through the current meter.

The 100nF capacitor discharges quite quickly
depending on the current gain (hFE) of the transistors.
Practically this means that the meters tend to show a lower value than you would expect.
Usually anything that depends on the current gain is considered bad design,
but in this case I think it's fine, because it's easy to work around in software:
I could use a higher frequency, or I can just send larger signals to compensate.

The small 1k "resistor" represents the op-amp's internal output resistance.
The datasheet says that the output resistance of a UA798TC is typically 800ohm,
but doesn't specify minimum or maximum values.


## Software Setup

The software assumes that you have linux. Specifically, it uses:
- `aplay` to play audio
- `aplay -L` to list audio devices
- `/proc/stat` to get CPU usage
- `/proc/meminfo` to get RAM usage.

The advantage is that there are no dependencies except development tools and Python's standard library.
Let me know if you need to run or develop the software on something else than Linux.

I made an ugly but useful tkinter GUI to compensate for electronics inaccuracies in software.

```
$ python3 -m mittari config
```

The GUI looks like this:

![config GUI](config-screenshot.png)

Each slider sets the audio volume used to move the meter to a given position.
As you hover or drag the sliders, the meter shows the value set by the slider,
so that you know where the slider should be.

Linear interpolation is used.
For example, to move the meter to 65%,
the software will play audio whose volume is the average of the 60% and 70% sliders.

Once configured, you can start displaying CPU and memory usage:

```
$ python3 -m mittari
```

If you want to develop the software, you should probably start with these commands:

```
$ python3 -m venv
$ source env/bin/activate
$ pip install -r requirements-dev.txt
$ mypy mittari          # type checker
$ python3 -m pytest     # run tests
```
