#!/usr/bin/env python
# Script to validate just the problematic function

def extract_function(filename, function_name):
    with open(filename, 'r') as f:
        content = f.read()
    
    import re
    # Look for the function definition
    pattern = f"@login_required\ndef {function_name}.*?(?=\n\n[^ \n])"
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        function_text = match.group(0)
        print(f"Extracted function {function_name}:")
        print("="*50)
        print(function_text)
        print("="*50)
        
        # Try to compile the function
        try:
            compile(function_text, '<string>', 'exec')
            print("Function compiles successfully!")
        except SyntaxError as e:
            print(f"Syntax error: {e}")
            print(f"Error at line {e.lineno}, position {e.offset}")
            lines = function_text.split('\n')
            for i, line in enumerate(lines):
                if i == e.lineno - 1:
                    print(f"> {line}")
                    print(f"  {' ' * (e.offset - 1)}^")
                else:
                    print(f"  {line}")
    else:
        print(f"Function {function_name} not found in {filename}")

if __name__ == "__main__":
    extract_function('myapp/views.py', 'impose_fine') 