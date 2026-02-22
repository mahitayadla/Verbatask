import re

def parse_transcript(raw_transcript):
    messages = []
    lines = raw_transcript.splitlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # skip WEBVTT header, blank lines, and message numbers and timestamp lines
        if not line or line == "WEBVTT" or line.isdigit():
            i += 1
            continue
        
        if "-->" in line:
            i += 1

            if i < len(lines):
                text_line = lines[i].strip()
                match = re.match(r'(.*?):\s+(.*)', text_line)
                if match:
                    speaker, text = match.groups()
                    messages.append({
                        "speaker": speaker.strip(),
                        "text": text.strip()
                    })
            i += 1
            continue
        
        i += 1
    return messages