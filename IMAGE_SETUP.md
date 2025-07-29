# Image Generation Setup Guide

This chat system now supports AI image generation using Stable Diffusion! Here's how to set it up:

## Quick Start (Mock Mode)
The system works out of the box and will create mock responses when no image generation backend is available.

## Full Setup with Stable Diffusion WebUI

### 1. Install AUTOMATIC1111's Stable Diffusion WebUI

```bash
# Clone the repository
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
cd stable-diffusion-webui

# Fix PyTorch version compatibility (IMPORTANT)
# Edit webui-user.bat and add this line before running:
# set TORCH_COMMAND=pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cu121

# Install dependencies (Windows) - Run this after editing webui-user.bat
webui-user.bat

# Alternative for Windows if the above fails:
# Double-click webui-user.bat in File Explorer
# OR use Command Prompt (not PowerShell):
# cmd
# cd stable-diffusion-webui
# webui-user.bat

# Install dependencies (Linux/Mac)
./webui.sh
```

**IMPORTANT FIX for PyTorch Error:**

If you get a PyTorch version error, edit `webui-user.bat` file and add this line:

```batch
set TORCH_COMMAND=pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cu121
```

The file should look like this:
```batch
@echo off

set PYTHON=C:\Users\herzi\miniconda3\envs\310\python.exe
set GIT=
set VENV_DIR=
set COMMANDLINE_ARGS=--skip-torch-cuda-test --api
set TORCH_COMMAND=pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

call webui.bat
```

**Important Notes:**
- Replace the Python path with your actual conda environment path
- Use `conda run --name YOUR_ENV python -c "import sys; print(sys.executable)"` to find your path
- The `--skip-torch-cuda-test` flag is important if you have GPU issues

### 2. Download a Stable Diffusion Model

1. Go to [Hugging Face](https://huggingface.co/models?pipeline_tag=text-to-image) or [Civitai](https://civitai.com/)
2. Download a model (e.g., `v1-5-pruned-emaonly.safetensors`)
3. Place it in the `stable-diffusion-webui/models/Stable-diffusion/` folder

### 3. Start WebUI with API Access

```bash
# Windows
./webui-user.bat --api

# Linux/Mac  
./webui.sh --api
```

The WebUI will start on `http://localhost:7860`

### 4. Test Image Generation

Now you can ask the chat system to generate images:

- "Generate an image of a sunset over mountains"
- "Create a picture of a cute cat wearing a hat"
- "Draw a futuristic city with flying cars"
- "Make an image of a peaceful forest scene"

## How It Works

1. **Image Request Detection**: The system detects when you're asking for image generation
2. **Prompt Extraction**: Uses the LLM to extract and improve the image description
3. **API Call**: Sends the prompt to the Stable Diffusion WebUI API
4. **Image Saving**: Saves generated images to `generated_images/` folder
5. **Response**: Provides you with the file path and generation details

## Supported Phrases

The system recognizes these types of requests:
- "generate image of..."
- "create picture of..."
- "draw..."
- "show me an image of..."
- "make a picture of..."
- "visualize..."
- "paint..."
- "sketch..."

## Files and Folders

- `generated_images/` - Where all generated images are saved
- Images are named with timestamp and prompt: `20250128_143022_sunset_mountains.png`
- Mock files end with `_MOCK.txt` when no backend is available

## Troubleshooting

### PyTorch Version Error (Common Issue)
**Error:** `Could not find a version that satisfies the requirement torch==2.1.2`

**Solution:**
1. Navigate to your `stable-diffusion-webui` folder
2. Edit `webui-user.bat` file
3. Add this line after the `@echo off` line:
   ```batch
   set TORCH_COMMAND=pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cu121
   ```
4. Save the file and run `webui-user.bat` again

**Alternative Solution:**
If the above doesn't work, try this command in the stable-diffusion-webui folder:
```bash
# Delete the venv folder to start fresh
rmdir /s venv

# Activate the virtual environment first
venv\Scripts\activate

# Install latest compatible PyTorch
pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cu121

# Then run the webui
webui-user.bat --api
```

**Force Update Method (Most Reliable):**
If the TORCH_COMMAND setting is being ignored, manually install PyTorch first:

```batch
# 1. Delete the existing virtual environment
rmdir /s /q venv

# 2. Create a new virtual environment
python -m venv venv

# 3. Activate it
venv\Scripts\activate

# 4. Install latest PyTorch manually
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 5. Install other requirements
pip install -r requirements.txt

# 6. Now run the webui
python launch.py --api
```

### Python Version Issues
**Error:** `INCOMPATIBLE PYTHON VERSION - This program is tested with 3.10.6 Python, but you have 3.13.5`

**Solution:**
1. **Find your Python 3.10 path:**
   ```bash
   conda run --name YOUR_310_ENV python -c "import sys; print(sys.executable)"
   ```

2. **Set the Python path in webui-user.bat:**
   ```batch
   set PYTHON=C:\Users\YourUser\miniconda3\envs\310\python.exe
   ```

3. **Create Python 3.10 conda environment if needed:**
   ```bash
   conda create -n py310 python=3.10
   conda activate py310
   ```

### Build Environment Issues
**Error:** `FileNotFoundError: [WinError 2] Das System kann die angegebene Datei nicht finden` during pip install

**Solutions:**
1. **Install Microsoft Visual C++ Build Tools:**
   - Download and install [Microsoft Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
   - Or install [Visual Studio Community](https://visualstudio.microsoft.com/vs/community/) with C++ development tools

2. **Use Pre-compiled Wheels (Recommended):**
   ```batch
   # Delete venv and start fresh
   rmdir /s /q venv
   
   # Create new venv with conda Python
   C:\Users\herzi\miniconda3\envs\310\python.exe -m venv venv
   
   # Activate venv
   venv\Scripts\activate
   
   # Install PyTorch with pre-compiled wheels
   pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118
   
   # Install other basic requirements
   pip install transformers accelerate safetensors
   ```

3. **Alternative: Use conda for problematic packages:**
   ```batch
   # Install main packages via conda
   conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
   
   # Then run webui
   python launch.py --api --skip-torch-cuda-test
   ```

4. **Skip problematic installations:**
   ```batch
   # Start with minimal installation
   set COMMANDLINE_ARGS=--skip-torch-cuda-test --api --skip-python-version-check --skip-install
   ```

### GPU/CUDA Issues
**Error:** `Torch is not able to use GPU; add --skip-torch-cuda-test to COMMANDLINE_ARGS`

**Solutions:**
1. **Quick Fix:** Add `--skip-torch-cuda-test` to COMMANDLINE_ARGS in webui-user.bat:
   ```batch
   set COMMANDLINE_ARGS=--skip-torch-cuda-test --api
   ```

2. **Check CUDA Installation:**
   ```bash
   # Check if NVIDIA driver is installed
   nvidia-smi
   
   # Check CUDA version
   nvcc --version
   ```

3. **Verify PyTorch CUDA Support:**
   ```python
   # Run this in Python to test
   import torch
   print(f"PyTorch version: {torch.__version__}")
   print(f"CUDA available: {torch.cuda.is_available()}")
   print(f"CUDA version: {torch.version.cuda}")
   print(f"GPU count: {torch.cuda.device_count()}")
   if torch.cuda.is_available():
       print(f"GPU name: {torch.cuda.get_device_name(0)}")
   ```

4. **Reinstall PyTorch with Correct CUDA Version:**
   - Visit [PyTorch website](https://pytorch.org/get-started/locally/)
   - Select your CUDA version (check with `nvidia-smi`)
   - Run the recommended install command

### No Images Generated
1. Check if Stable Diffusion WebUI is running with `--api` flag
2. Verify it's accessible at `http://localhost:7860`
3. Check the console for error messages

### API Connection Issues
- Make sure no firewall is blocking localhost:7860
- Try restarting the WebUI with `--api --listen` for network access

### Poor Image Quality
- Try using more descriptive prompts
- The system automatically adds negative prompts for better quality
- You can modify the generation parameters in the code

## Advanced Configuration

You can modify these settings in `main.py`:

```python
payload = {
    "prompt": prompt,
    "negative_prompt": "blurry, low quality, distorted, ugly, bad anatomy",
    "steps": 20,           # More steps = better quality, slower generation
    "width": 512,          # Image width
    "height": 512,         # Image height  
    "cfg_scale": 7,        # How closely to follow the prompt
    "sampler_name": "DPM++ 2M Karras"  # Sampling method
}
```

## Alternative APIs

The code is designed to be extensible. You can add support for:
- Stability AI API
- OpenAI DALL-E API
- Other Stable Diffusion services

Just implement the corresponding generation method and add it to the fallback chain.

## Example Usage

```
You: Generate an image of a majestic dragon flying over a medieval castle
