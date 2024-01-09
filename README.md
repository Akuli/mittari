# Mittari

This electronics+software project adds analog CPU and RAM usage meters to my computer.

TODO: picture

The meters are controlled by sending audio out through the headphones jack.
This turned out to be the most convenient way to control an analog circuit with my computer.
Also, because the headphones jack supports stereo,
I conveniently get two channels (left and right) that I can use for the two meters.
The only downside is that if I connect my headphones to the wrong place,
I will hear annoying and loud 1kHz beeping.

Here is the circuit that drives the meters based on the headphones signal:

TODO: screenshot

TODO: explain circuit

The actual meters are [this product from AliExpress](https://www.aliexpress.com/item/1005004735059319.html).
I used the 5mA version.


## Setup

After constructing the circuit above and plugging
