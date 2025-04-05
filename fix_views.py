import re

# Define the corrected code block with proper indentation
corrected_block = '''            try:
                # Get or validate vehicle
                reg_number = form.cleaned_data['vehicle_registration_number']
            
                # Normalize the registration number (remove spaces, convert to uppercase)
                normalized_reg = normalize_registration_number(reg_number)
                if not normalized_reg:
                    messages.error(request, f"Invalid registration number format: {reg_number}")
                    return render(request, 'impose_fine.html', {'form': form})
                
                # Try to find the vehicle with the normalized registration number
                try:
                    vehicle = Vehicle.objects.get(registration_number=normalized_reg)
                except Vehicle.DoesNotExist:
                    # Try with the original input as a fallback
                    vehicle = Vehicle.objects.get(registration_number=reg_number)'''

# Read the file
try:
    with open('myapp/views.py', 'r', encoding='utf-8') as file:
        content = file.read()
except:
    # Try with a different encoding if needed
    with open('myapp/views.py', 'r') as file:
        content = file.read()

# Find the problematic section
pattern = r'try:\s*# Get or validate vehicle\s*reg_number = form\.cleaned_data\[\'vehicle_registration_number\'\]'
match = re.search(pattern, content, re.DOTALL)

if match:
    # Get the position of the match
    start_pos = match.start()
    
    # Find the line containing "try:"
    line_start = content.rfind('\n', 0, start_pos) + 1
    
    # Extract the indentation before the try block
    indentation = ''
    for char in content[line_start:start_pos]:
        if char in ' \t':
            indentation += char
    
    # Get everything before the problematic section
    before_section = content[:line_start]
    
    # Find where to end the replacement (after "vehicle = Vehicle.objects.get(registration_number=reg_number)")
    fallback_pattern = r'vehicle = Vehicle\.objects\.get\(registration_number=reg_number\)'
    fallback_match = re.search(fallback_pattern, content[start_pos:])
    
    if fallback_match:
        end_pos = start_pos + fallback_match.end()
        
        # Get everything after the section to replace
        after_section = content[end_pos:]
        
        # Construct the new content
        new_content = before_section + corrected_block + after_section
        
        # Write the corrected content back to the file
        with open('myapp/views.py', 'w', encoding='utf-8') as file:
            file.write(new_content)
        
        print("Successfully fixed indentation in views.py")
    else:
        print("Could not locate the end of the section to replace")
else:
    print("Could not find the problematic section in views.py")

def fix_views():
    print("Fixing indentation in views.py...")
    
    # Read the file content
    with open('myapp/views.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the start of the impose_fine function
    impose_fine_start = -1
    for i, line in enumerate(lines):
        if 'def impose_fine(request):' in line:
            impose_fine_start = i
            break
    
    if impose_fine_start == -1:
        print("Could not find the impose_fine function in views.py")
        return
    
    # Find the next function definition to determine the end of impose_fine
    impose_fine_end = -1
    for i in range(impose_fine_start + 1, len(lines)):
        if 'def ' in lines[i] and '(' in lines[i] and '):' in lines[i]:
            impose_fine_end = i
            break
    
    if impose_fine_end == -1:
        print("Could not find the end of impose_fine function")
        return
    
    # Extract the function content
    function_lines = lines[impose_fine_start:impose_fine_end]
    
    # Fix indentation issues in lines 609-611 (which might have different line numbers in the file)
    fixed_lines = []
    
    in_try_block = False
    
    for i, line in enumerate(function_lines):
        if '            try:' in line:
            in_try_block = True
            fixed_lines.append(line)
        elif in_try_block and ('reg_number =' in line or 'normalized_reg =' in line or 'if not normalized_reg:' in line):
            # Fix the indentation for these lines
            fixed_line = line.replace('            ', '                ')
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
    
    # Replace the function in the file
    new_lines = lines[:impose_fine_start] + fixed_lines + lines[impose_fine_end:]
    
    # Write back to the file
    with open('myapp/views.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print("Successfully fixed indentation in impose_fine function")

if __name__ == "__main__":
    fix_views() 