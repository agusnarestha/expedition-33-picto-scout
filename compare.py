import difflib

MASTER_LIST_FILE = "master_list.txt"
DETECTED_LIST_FILE = "output/detected_pictos.txt"
MISSING_LIST_FILE = "output/missing_pictos.txt"

def main():
    # 1. Load Master List
    with open(MASTER_LIST_FILE, 'r', encoding='utf-8') as f:
        master_list = [line.strip() for line in f if line.strip()]

    # 2. Load Detected List
    detected_list = []
    try:
        with open(DETECTED_LIST_FILE, 'r', encoding='utf-8') as f:
            detected_list = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: {DETECTED_LIST_FILE} not found. Run scout.py first.")
        return

    print(f"Master List: {len(master_list)} items")
    print(f"Detected List: {len(detected_list)} items")

    found_in_master = set()
    missing_from_user = []

    # 3. Compare Logic (Fuzzy Match)
    # For every item in master list, check if it exists in detected list (fuzzy)
    for master_item in master_list:
        # Check for exact match first
        if master_item in detected_list:
            found_in_master.add(master_item)
            continue
        
        # Check for close match (OCR typo tolerance)
        # get_close_matches returns a list of possibilities.
        # cutoff=0.8 means 80% similarity required.
        matches = difflib.get_close_matches(master_item, detected_list, n=1, cutoff=0.8)
        
        if matches:
            found_in_master.add(master_item)
            # print(f"  Matched '{master_item}' with '{matches[0]}'") -- Verbose
        else:
            missing_from_user.append(master_item)

    # 4. Report Results
    print(f"\n--- RESULTS ---")
    print(f"You have {len(found_in_master)} out of {len(master_list)} known pictos.")
    print(f"Missing: {len(missing_from_user)}")
    
    with open(MISSING_LIST_FILE, 'w', encoding='utf-8') as f:
        f.write("# Missing Pictos (Based on Master List)\n")
        f.write("# Note: This depends on the accuracy of 'master_list.txt' and OCR quality.\n\n")
        for item in missing_from_user:
            f.write(item + "\n")
            print(f"  [MISSING] {item}")

    print(f"\nMissing list saved to {MISSING_LIST_FILE}")

if __name__ == "__main__":
    main()
