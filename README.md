# drone-project
# Install Edge TPU compiler on your host system (WSL or Ubuntu)

curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list

sudo apt-get update

sudo apt-get install edgetpu-compiler

# 1. On your local machine (with GPU)

python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

python train.py

python recompile.py


# 2. Copy to Raspberry Pi

scp "yolo_coral_training/run_720/weights/best_saved_model/best_full_integer_quant_edgetpu.tflite" labels.txt coral_yolo_detector.py install_raspberry_pi.sh tpu@drone.local:~/

# 3. On Raspberry Pi

chmod +x install_raspberry_pi.sh

./install_raspberry_pi.sh

# (reboot)

python coral_yolo_detector.py --model best_full_integer_quant_edgetpu.tflite --labels labels.txt
