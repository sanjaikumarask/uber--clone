import os
import xml.etree.ElementTree as ET

def diagnose_paths():
    xml_path = "backend/coverage.xml"
    if not os.path.exists(xml_path):
        print(f"File {xml_path} not found.")
        return
        
    tree = ET.parse(xml_path)
    root = tree.getroot()
    broken_files = []
    
    # Extract all filename paths
    for package in root.findall(".//package"):
        for cls in package.findall(".//class"):
            filename = cls.get("filename")
            if filename:
                # Based on our source=".", Sonar expects the file to be exactly at `filename` 
                # resolving from project root where scanner executes.
                if not os.path.exists(filename):
                    broken_files.append(filename)
                    
    if len(broken_files) > 0:
        print(f"❌ FOUND {len(broken_files)} FILES THAT DO NOT EXIST ON DISK:")
        for bf in broken_files[:10]:
            print(f" - Missing: {bf}")
            
        print("\nFix suggestions:")
        for bf in broken_files[:3]:
            # Simple assumption check
            guess = "backend/" + bf if not bf.startswith("backend/") else bf.replace("backend/", "")
            if os.path.exists(guess):
                print(f" {bf} -> SHOULD LIKELY BE -> {guess}")
            else:
                print(f" {bf} -> Path on disk totally unmatched.")
    else:
        print("✅ SUCCESS! All paths in coverage.xml resolve correctly to physical files.")

if __name__ == "__main__":
    diagnose_paths()
