#!/bin/bash

# Guillemot LLM Chat App Launcher
# This script runs the terminal-based LLM chat application

echo "🎯 Starting Guillemot LLM Chat App..."
echo "Make sure your .env file is configured with GEMINI_API_KEY"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Please create a .env file with your GEMINI_API_KEY"
    echo ""
fi

# Run the Python application using the virtual environment
exec ./.venv/bin/python main.py
