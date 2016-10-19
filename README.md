# simplesim
Simple, sparsely featured simulator for AVR microcontrollers

If you've stumbled across this hoping for an AVR simulator, I'm afraid this is nowhere near ready for general use. It's mostly an experiment for my own edification, though it would be great if some day it became useful to a wider audience. Basically, I'm building a simulator for AVRs so that I can build a compiler for it (again, mostly for learning).

Roadmap
=======

* Create a simple assembler for a reasonable subset of the AMR instruction set.
  * output to an in-memory representation of the instructions.
  * later, add ability to emit actual AVR .hex files
  
* Create a simulator that will run said AVR code
  * Initially, concentrate on the core CPU instructions, disregarding peripherals
  * Don't worry about timing, but track CPU state as accurately as possible
  * Develop tools for inspecting CPU state (reg/mem/etc)
  
* Further work
  * Develop a GUI for interacting with the simulator
  * Add cycle timing information
  * Handle peripheral IO
