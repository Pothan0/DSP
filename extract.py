import zipfile
import xml.etree.ElementTree as ET
import glob

files = glob.glob(r'C:\Users\sarag\Downloads\DSP_*.docx')
with open(r'c:\Users\sarag\Downloads\DSP_PROJECT\assignments.txt', 'w', encoding='utf-8') as f:
    for file in files:
        f.write(f"\n\n--- FILE: {file} ---\n\n")
        try:
            doc = zipfile.ZipFile(file)
            content = doc.read('word/document.xml')
            root = ET.fromstring(content)
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            for p in root.findall('.//w:p', ns):
                p_text = ''.join([t.text for t in p.findall('.//w:t', ns) if t.text])
                if p_text:
                    f.write(p_text + "\n")
        except Exception as e:
            f.write(f"Error reading {file}: {e}\n")
