import os
import xml.etree.ElementTree as ET

def fix_coverage_paths():
    xml_path = "backend/coverage.xml"
    if not os.path.exists(xml_path):
        print(f"File {xml_path} not found.")
        return
        
    tree = ET.parse(xml_path)
    root = tree.getroot()
    fixed_count = 0
    
    # 1. Update source
    sources = root.find("sources")
    if sources is not None:
        sources.clear()
        new_source = ET.SubElement(sources, "source")
        # Dot resolves relative to where sonar-scanner runs from (project root)
        new_source.text = "."
    
    # 2. Extract and fix all filename paths
    for package in root.findall(".//package"):
        for cls in package.findall(".//class"):
            filename = cls.get("filename")
            if filename:
                original = filename
                
                # Strip absolute /app/ if it exists
                if filename.startswith("/app/"):
                    filename = filename[5:]
                
                # Check where it lives on the host
                if os.path.exists("backend/apps/" + filename):
                    new_filename = "backend/apps/" + filename
                elif os.path.exists("backend/consumers/" + filename):
                    new_filename = "backend/consumers/" + filename
                elif os.path.exists("backend/" + filename):
                    new_filename = "backend/" + filename
                else:
                    new_filename = filename # Fallback if not found
                    
                if new_filename != original:
                    cls.set("filename", new_filename)
                    fixed_count += 1

    tree.write(xml_path, encoding="utf-8", xml_declaration=True)
    print(f"Fixed {fixed_count} paths accurately mapping to disk.")

if __name__ == "__main__":
    fix_coverage_paths()
