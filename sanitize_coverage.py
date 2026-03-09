import xml.etree.ElementTree as ET
import os

def sanitize_coverage(xml_path, base_dir):
    if not os.path.exists(xml_path):
        return

    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    modified = False
    
    # Empty all source tags so Sonar relies fully on the relative filenames we set
    for source_node in root.findall(".//source"):
        source_node.text = ""
        modified = True

    # Prepend backend/ to match Sonar's project root perspective
    for clazz in root.findall(".//class"):
        filename = clazz.get("filename")
        if not filename:
            continue
            
        # If it doesn't already start with backend/, prepend it!
        if not filename.startswith("backend/"):
            new_filename = f"backend/{filename}"
            clazz.set("filename", new_filename)
            modified = True
        else:
            new_filename = filename
            
        full_path = new_filename # Since the script runs from project root now
        if not os.path.exists(full_path):
            continue
            
        with open(full_path, 'r') as f:
            lines = f.readlines()
            line_count = len(lines)
            
        lines_node = clazz.find("lines")
        if lines_node is not None:
            for line in lines_node.findall("line"):
                num = int(line.get("number"))
                if num > line_count:
                    print(f"Removing invalid line {num} from {filename} (file has {line_count} lines)")
                    lines_node.remove(line)
                    modified = True
                    
    if modified:
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
        print(f"Sanitized {xml_path}")

if __name__ == "__main__":
    sanitize_coverage("backend/coverage.xml", "backend")
