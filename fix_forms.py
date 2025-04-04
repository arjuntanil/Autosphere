import re

# Define the corrected method with proper indentation
corrected_method = '''    def clean_violation_documents(self):
        """Validate that all uploaded files are valid PDF documents or images"""
        documents = self.cleaned_data.get('violation_documents')
        valid_documents = []
        
        if not documents:
            return valid_documents
        
        # Convert to list if it's a single file
        if not isinstance(documents, (list, tuple)):
            documents = [documents]
        
        for document in documents:
            if document:
                # Check file extension
                file_ext = os.path.splitext(document.name)[1].lower()
                allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
                
                if file_ext not in allowed_extensions:
                    raise forms.ValidationError(f"Only PDF and image files (JPG, JPEG, PNG) are allowed. Got {file_ext}")
                
                # Check file size (limit to 5MB)
                if document.size > 5 * 1024 * 1024:  # 5MB in bytes
                    raise forms.ValidationError(f"File size must be under 5MB. '{document.name}' is {document.size/1024/1024:.2f}MB")
                    
                # Validate MIME type (additional check for security)
                valid_mimetypes = [
                    'application/pdf',  # PDF
                    'image/jpeg',       # JPG, JPEG
                    'image/png'         # PNG
                ]
                
                # Check content type from the uploaded file
                content_type = document.content_type if hasattr(document, 'content_type') else None
                
                # Try to use python-magic if available, but fallback gracefully if not
                try:
                    import magic
                    # Reset file pointer to beginning before reading
                    document.seek(0)
                    file_mime = magic.from_buffer(document.read(1024), mime=True)
                    # Reset file pointer after reading
                    document.seek(0)
                    
                    if file_mime not in valid_mimetypes:
                        raise forms.ValidationError(f"Invalid file type detected for '{document.name}': {file_mime}")
                except (ImportError, ModuleNotFoundError):
                    # Fallback to basic extension checking and content_type if magic is not available
                    if content_type and content_type not in valid_mimetypes:
                        # If content_type is available and invalid, raise error
                        raise forms.ValidationError(f"Invalid file type for '{document.name}': {content_type}")
                    else:
                        # Just use extension checking as a fallback
                        # Map extensions to expected content types
                        ext_to_content_type = {
                            '.pdf': 'application/pdf',
                            '.jpg': 'image/jpeg',
                            '.jpeg': 'image/jpeg',
                            '.png': 'image/png'
                        }
                        # Check that the extension matches expected pattern
                        # This is a simple check but better than nothing when magic isn't available
                        expected_content_type = ext_to_content_type.get(file_ext)
                        if content_type and expected_content_type and content_type != expected_content_type:
                            raise forms.ValidationError(
                                f"File extension ({file_ext}) doesn't match content type ({content_type}) for '{document.name}'"
                            )
                
                valid_documents.append(document)
        
        return valid_documents'''

# Read the original file
try:
    with open('myapp/forms.py', 'r', encoding='utf-8') as file:
        content = file.read()
except:
    # Try with a different encoding if needed
    with open('myapp/forms.py', 'r') as file:
        content = file.read()

# Define pattern to find the method with appropriate context
pattern = r'def clean_violation_documents\(self\):.*?def clean_fine_amount\(self\):'
# Use re.DOTALL to match across multiple lines
match = re.search(pattern, content, re.DOTALL)

if match:
    # Extract the matched method and create the replacement
    old_method = match.group(0)
    # Remove the next method declaration that was captured in our pattern
    next_method_decl = 'def clean_fine_amount(self):'
    replacement = corrected_method + '\n\n    ' + next_method_decl
    
    # Replace the old method with the corrected version
    new_content = content.replace(old_method, replacement)
    
    # Write the corrected content back to the file
    with open('myapp/forms.py', 'w', encoding='utf-8') as file:
        file.write(new_content)
    
    print("Successfully fixed indentation in clean_violation_documents method")
else:
    print("Could not find the clean_violation_documents method in forms.py") 