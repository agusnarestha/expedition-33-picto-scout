import cv2
import pyautogui
import easyocr
import time
import os
import re
from PIL import Image
import compare # Import the comparison logic

# --- CONFIGURATION ---
OUTPUT_DIR = "output"
RAW_DIR = os.path.join(OUTPUT_DIR, "raw")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "detected_pictos.txt")

# --- CONFIGURATION ---
OUTPUT_DIR = "output"
RAW_DIR = os.path.join(OUTPUT_DIR, "raw")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "detected_pictos.txt")

# Capture Settings
SCROLL_STEPS = 25     # Increased to ensure we reach the bottom
SCROLL_AMOUNT = -1000 # Approx one "page" down
SLEEP_BETWEEN_SCROLLS = 2

# Processing Settings
# focus_box = (left_pct, top_pct, right_pct, bottom_pct)
FOCUS_BOX = (0.0, 0.20, 0.50, 0.90) # ROI for Text Detection (Content)

# Scroll Bar ROI: (Left, Top, Right, Bottom)
# Targeting the thin strip on the left where the scroll indicator moves
SCROLL_BAR_BOX = (0.02, 0.20, 0.08, 0.90) 

def clean_text(text_list):
    """Cleans up the OCR text."""
    cleaned = []
    for line in text_list:
        line = line.strip()
        # Filter out very short noise and numeric-only noise often found in UI headers
        if len(line) > 3 and not line.isdigit(): 
             cleaned.append(line)
    return cleaned

def preprocess_image(img):
    """Converts to grayscale and applies thresholding to make text pop."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Binary threshold: Make bright text white and background black
    # Adjust 150 based on text brightness if needed
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    return thresh

import numpy as np

def images_are_similar(img1, img2, threshold=1000):
    """Checks if the SCROLL BAR has stopped moving."""
    if img1.shape != img2.shape:
        return False

    # 1. Convert to grayscale
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # 2. Crop to the SCROLL BAR AREA
    h, w = gray1.shape
    x1 = int(w * SCROLL_BAR_BOX[0])
    y1 = int(h * SCROLL_BAR_BOX[1])
    x2 = int(w * SCROLL_BAR_BOX[2])
    y2 = int(h * SCROLL_BAR_BOX[3])
    
    crop1 = gray1[y1:y2, x1:x2]
    crop2 = gray2[y1:y2, x1:x2]
    
    # 3. Simple Diff (No thresholding needed for UI elements usually, but keeping it safe)
    diff = cv2.absdiff(crop1, crop2)
    _, thresh_diff = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)
    non_zero_count = np.count_nonzero(thresh_diff)
    
    # IMPORTANT: Save the scroll bar view so user can debug if we are looking at the right spot
    if not os.path.exists(RAW_DIR): os.makedirs(RAW_DIR)
    cv2.imwrite(os.path.join(RAW_DIR, "debug_scroll_bar.png"), crop1)
    
    print(f"  [DEBUG] Scroll Bar Diff: {non_zero_count} (Threshold: {threshold})")
    
    return non_zero_count < threshold

def capture_phase():
    if not os.path.exists(RAW_DIR):
        os.makedirs(RAW_DIR)

    print("!!! PREPARE THE GAME !!!")
    print("You have 5 seconds to switch to the Expedition 33 window.")
    print("Make sure the list of pictos is visible.")
    for i in range(5, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    print("STARTING CAPTURE PHASE!")
    
    # 1. Move mouse OVER the list to ensure scroll works
    #    Targeting roughly x=10%, y=50% of screen (safe guess for left-side list)
    screen_w, screen_h = pyautogui.size()
    target_x = int(screen_w * 0.15)
    target_y = int(screen_h * 0.5)
    
    print(f"Moving mouse to ({target_x}, {target_y}) to focus list...")
    pyautogui.moveTo(target_x, target_y) 
    time.sleep(1) # Wait for focus

    previous_frame = None

    previous_frame = None

    for step in range(SCROLL_STEPS):
        print(f"--- Capture Step {step + 1}/{SCROLL_STEPS} ---")
        
        timestamp = int(time.time())
        screenshot_path = os.path.join(RAW_DIR, f"screen_{step:02d}_{timestamp}.png")
        
        # Capture and convert to OpenCV format for comparison
        screenshot = pyautogui.screenshot()
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Check for duplicates (End of List Detection)
        if previous_frame is not None:
            if images_are_similar(frame, previous_frame):
                print("🛑 Screen stopped changing. Reached end of list! Stopping capture.")
                break
        
        previous_frame = frame
        
        # Save
        cv2.imwrite(screenshot_path, frame)
        print(f"Saved: {screenshot_path}")

        if step < SCROLL_STEPS - 1:
            pyautogui.scroll(SCROLL_AMOUNT)
            time.sleep(SLEEP_BETWEEN_SCROLLS)
    
    print("Capture complete.")

def processing_phase():
    print("\nSTARTING PROCESSING PHASE...")
    print("Initializing EasyOCR...")
    reader = easyocr.Reader(['en'], gpu=True) 
    
    all_pictos = set()
    
    # Get all png files in raw dir
    files = [f for f in os.listdir(RAW_DIR) if f.endswith('.png')]
    files.sort() # Process in order

    for filename in files:
        filepath = os.path.join(RAW_DIR, filename)
        print(f"Processing {filename}...")
        
        # Load image
        img = cv2.imread(filepath)
        if img is None:
            continue
            
        # Crop to Focus Box
        h, w, _ = img.shape
        x1 = int(w * FOCUS_BOX[0])
        y1 = int(h * FOCUS_BOX[1])
        x2 = int(w * FOCUS_BOX[2])
        y2 = int(h * FOCUS_BOX[3])
        
        cropped_img = img[y1:y2, x1:x2]
        
        # Preprocess
        processed_img = preprocess_image(cropped_img)
        
        # Debug: Save debug images
        debug_path = os.path.join(RAW_DIR, f"debug_proc_{filename}")
        cv2.imwrite(debug_path, processed_img)
        
        # OCR
        results = reader.readtext(processed_img, detail=0)
        cleaned = clean_text(results)
        
        print(f"  Found {len(cleaned)} items.")
        for item in cleaned:
            all_pictos.add(item)

    # Save Results
    sorted_pictos = sorted(list(all_pictos))
    print(f"\n--- DONE! Found {len(sorted_pictos)} unique items ---")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for picto in sorted_pictos:
            f.write(picto + "\n")
            print(picto)
    
    print(f"Results saved to {OUTPUT_FILE}")

def main():
    # Ask mode
    print("Select Mode:")
    print("1. Capture + Process + Compare (Full Run)")
    print("2. Process + Compare (Skip Capture)")
    print("3. Compare Only (Check missing from existing results)")
    choice = input("Enter 1, 2, or 3: ").strip()

    if choice == '1':
        capture_phase()
        processing_phase()
        print("\n--- Running Comparison ---")
        compare.main()
    elif choice == '2':
        processing_phase()
        print("\n--- Running Comparison ---")
        compare.main()
    elif choice == '3':
        print("\n--- Running Comparison ---")
        compare.main()
    else:
        print("Invalid choice. Exiting.")


if __name__ == "__main__":
    main()
