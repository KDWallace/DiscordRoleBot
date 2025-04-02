::Everything here is entirely decorative
@echo off
set title=Deleting System 33...
title %title%
::mode con cols=78
set version=Discord Role Bot V1.1.2

::Runs the actual code using the provided python exe and libraries
"%~dp0.venv/Scripts/python.exe" "%~dp0src/Bot.py" %version%


::if the code stops unexpectedly, something bad probably happened...
@echo Something went wrong here
pause
