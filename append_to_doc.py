import sys
import os

def append_to_file(filename, content):
    with open(filename, 'a') as f:
        f.write(content + "\n\n")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python append_to_doc.py <filename> <content_file>")
        sys.exit(1)
    
    filename = sys.argv[1]
    content_file = sys.argv[2]
    
    with open(content_file, 'r') as f:
        content = f.read()
        
    append_to_file(filename, content)
    print(f"Successfully appended to {filename}")