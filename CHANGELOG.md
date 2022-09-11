# Changelog

0.3.0 - (2022-09-05)
------------------

* Starting work on a new version of the cooler. Goal is to be much quieter and more responsive.
* Can accurately measure square waves (frequency/duty cycle) using PIO.
* Can accurately generate slow square waves, in the 1 Hz -> 100 KHz range.


0.2.2 - (2022-07-18)
------------------

* Fixed bugs in docs.


0.2.1 - (2021-10-27)
------------------

* Improved docs for publication.


0.2.0 - (2021-10-21)
------------------

* Implements a fan control algo that minimizes fan noise.
* Adds check to make sure fans won't stall when set to slow speeds.
* Implements fan speed curve, no PID though...
* Refactored main loop to use timers, so we can interact with the pico while the "application" is
running.


0.1.0 - (2021-10-08)
------------------

* First working version, controls fan speed with a very basic control method.


0.0.1 - (2021-10-02)
------------------

* Project begins
