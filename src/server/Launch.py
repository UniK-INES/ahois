"""
Main entry point for launching the Mesa visualisation server.

This script serves as the executable entry point to start the agent-based
model's interactive server.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
"""
from server.Server import server

server.launch()
