monopolpy
=========

[![Build Status](https://travis-ci.org/areku/monopolpy.png)](https://travis-ci.org/areku/monopolpy)
[![Coverage Status](https://coveralls.io/repos/areku/monopolpy/badge.png)](https://coveralls.io/r/areku/monopolpy)


A simple simulation of monopoly in python. 


LICENSE: gpl-v3 -- Author: Alexander Weigl <alexweigl@gmail.com>

The module emulates monopoly bases on the configuration in monopoly.field.yaml. 

working:
  * simple turns (dice, moving forward, event triggering)
  * calculation rent (double rent, ...)
  * money and ownership transfers
  * ...
  
not implementing: 
  * social and event cards (currently is uses a prng to calculate a suitable amount)
  * trading (especially async)
  * security and fraud checks 


Depends on a small module: colors for printing [colors](https://github.com/areku/colors) in ansi terminals. You can simple replace the cprint function with `print`.
