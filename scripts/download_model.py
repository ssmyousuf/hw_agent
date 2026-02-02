import os
import requests
import sys

# Configuration
MODEL_URL = "https://huggingface.co/Bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
MODEL_FILENAME = "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
DEST_PATH = os.path.join(MODELS_DIR, MODEL_FILENAME)

def download_file(url, dest_path):
    print(f"Downloading model to {dest_path}...")
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 8192
            
            with open(dest_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # Simple progress bar
                        done = int(50 * downloaded / total_size)
                        sys.stdout.write(f"\r[{'=' * done}{' ' * (50 - done)}] {downloaded//(1024*1024)}MB / {total_size//(1024*1024)}MB")
                        sys.stdout.flush()
        print("\nDownload complete!")
    except Exception as e:
        print(f"\nError downloading model: {e}")
        # Clean up partial file
        if os.path.exists(dest_path):
            os.remove(dest_path)
        sys.exit(1)

if __name__ == "__main__":
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)
    
    if os.path.exists(DEST_PATH):
        print(f"Model already exists at {DEST_PATH}")
    else:
        print(f"Starting download of {MODEL_FILENAME}...")
        download_file(MODEL_URL, DEST_PATH)
