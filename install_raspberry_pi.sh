#!/bin/bash
# Installation script for Raspberry Pi with Coral USB Accelerator
# Includes support for Pi Camera 2 and HTTP streaming
# Run with: chmod +x install_raspberry_pi.sh && ./install_raspberry_pi.sh

set -e

echo "=============================================="
echo "Coral Edge TPU Setup for Raspberry Pi"
echo "With Pi Camera 2 and HTTP Streaming Support"
echo "=============================================="
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "Warning: This script is designed for Raspberry Pi."
    echo "Continuing anyway..."
    echo ""
fi

# Add Coral repository
echo "Adding Coral Edge TPU repository..."
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list

# Add repository key
echo "Adding repository key..."
curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -

# Update package list
echo ""
echo "Updating package list..."
sudo apt-get update

# Install Edge TPU runtime
echo ""
echo "=============================================="
echo "Edge TPU Runtime Speed Selection"
echo "=============================================="
echo ""
echo "Choose Edge TPU runtime speed:"
echo "  1) Maximum speed (higher performance, may require cooling)"
echo "  2) Standard speed (recommended for most use cases)"
echo ""
read -p "Enter choice [1-2]: " choice

case $choice in
    1)
        echo "Installing maximum speed runtime..."
        sudo apt-get install -y libedgetpu1-max
        ;;
    2)
        echo "Installing standard speed runtime..."
        sudo apt-get install -y libedgetpu1-std
        ;;
    *)
        echo "Invalid choice, installing standard speed runtime..."
        sudo apt-get install -y libedgetpu1-std
        ;;
esac

# Install Python packages for Coral
echo ""
echo "Installing Python dependencies for Coral..."
sudo apt-get install -y python3-pycoral python3-opencv python3-pil python3-numpy

# Install Pi Camera 2 support (picamera2)
echo ""
echo "Installing Pi Camera 2 support..."
sudo apt-get install -y python3-picamera2 python3-libcamera

# Install Flask for HTTP streaming
echo ""
echo "Installing Flask for HTTP streaming..."
sudo apt-get install -y python3-flask

# Install additional Python dependencies via pip (if needed)
echo ""
echo "Installing additional Python packages..."
pip3 install --upgrade pip --break-system-packages 2>/dev/null || pip3 install --upgrade pip
pip3 install numpy pillow flask --break-system-packages 2>/dev/null || pip3 install numpy pillow flask

# Enable camera interface
echo ""
echo "=============================================="
echo "Configuring Camera"
echo "=============================================="

# Check if libcamera is working
echo "Testing camera configuration..."
if command -v libcamera-hello &> /dev/null; then
    echo "libcamera tools are available"
else
    echo "Installing libcamera tools..."
    sudo apt-get install -y libcamera-apps
fi

# Verify installation
echo ""
echo "=============================================="
echo "Verifying Installation"
echo "=============================================="

echo ""
echo "Checking for Edge TPU library..."
if ldconfig -p | grep -q "libedgetpu"; then
    echo "Edge TPU library found"
else
    echo "Edge TPU library not found"
fi

echo ""
echo "Checking Python imports..."
python -c "from pycoral.utils.edgetpu import make_interpreter; print('pycoral installed correctly')" 2>/dev/null || echo "pycoral import failed"
python -c "import cv2; print('OpenCV installed correctly')" 2>/dev/null || echo "OpenCV import failed"
python -c "import numpy; print('NumPy installed correctly')" 2>/dev/null || echo "NumPy import failed"
python -c "from flask import Flask; print('Flask installed correctly')" 2>/dev/null || echo "Flask import failed"
python -c "from picamera2 import Picamera2; print('picamera2 installed correctly')" 2>/dev/null || echo "picamera2 import failed (OK if using USB camera)"

# USB permissions for Coral
echo ""
echo "Setting up USB permissions for Coral device..."
sudo usermod -aG plugdev $USER
sudo usermod -aG video $USER

# Create udev rule for Coral USB Accelerator
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="1a6e", MODE="0664", GROUP="plugdev"' | sudo tee /etc/udev/rules.d/99-coral-accelerator.rules
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", MODE="0664", GROUP="plugdev"' | sudo tee -a /etc/udev/rules.d/99-coral-accelerator.rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Ensure camera is enabled in config
echo ""
echo "Checking camera configuration..."
if grep -q "^camera_auto_detect=1" /boot/firmware/config.txt 2>/dev/null || grep -q "^camera_auto_detect=1" /boot/config.txt 2>/dev/null; then
    echo "Camera auto-detect is enabled"
else
    echo "Enabling camera..."
    if [ -f /boot/firmware/config.txt ]; then
        echo "camera_auto_detect=1" | sudo tee -a /boot/firmware/config.txt
    elif [ -f /boot/config.txt ]; then
        echo "camera_auto_detect=1" | sudo tee -a /boot/config.txt
    fi
fi

echo ""
echo "=============================================="
echo "Installation Complete!"
echo "=============================================="
echo ""
echo "IMPORTANT: Please reboot your Raspberry Pi for all changes to take effect."
echo ""
echo "After reboot:"
echo ""
echo "1. Connect your Coral USB Accelerator"
echo ""
echo "2. Test camera with:"
echo "   libcamera-hello --timeout 5000"
echo ""
echo "3. For SSH remote viewing (recommended), run:"
echo "   python3 coral_yolo_detector.py --model <model>_edgetpu.tflite --labels labels.txt --stream"
echo "   Then open http://<pi-ip>:5000 in your browser"
echo ""
echo "4. For local display (requires monitor), run:"
echo "   python3 coral_yolo_detector.py --model <model>_edgetpu.tflite --labels labels.txt --use-camera"
echo ""
read -p "Would you like to reboot now? [y/N]: " reboot_choice
if [[ "$reboot_choice" =~ ^[Yy]$ ]]; then
    sudo reboot
fi
