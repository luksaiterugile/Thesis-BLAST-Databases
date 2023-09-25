#!/bin/bash

# Update package lists
echo "Updating package lists..."
sudo apt-get update

# Install ncbi-blast+
echo "Installing ncbi-blast+..."
sudo apt-get install -y ncbi-blast+

# Install redis-server
echo "Installing redis-server..."
sudo apt-get install -y redis-server

# Installation complete
echo "Installation complete!"
