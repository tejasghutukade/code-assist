import os
from tree_sitter import Language, Parser

class SpringProjectParser:
    def __init__(self, directory):
        self.directory = directory
        self.parser = Parser()
        self.languages = {
            # 'java': Language('tree-sitter-languages/my-language-java.so', 'java'),
            # 'kotlin': Language('tree-sitter-languages/my-language-kotlin.so', 'kotlin'),  # Make sure to add the Kotlin grammar
            'java': Language('build/my-languages.so', 'java'),
            'kotlin': Language('build/my-languages.so', 'kotlin')
        }
        self.definitions = {}  # key: (type, name, package, language), value: definition
        self.usages = {}  # key: (type, name, package, language), value: list of usages
        self._parse_directory()

    def _parse_directory(self):
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                if file.endswith(".java") or file.endswith(".kt"):
                    language_key = 'java' if file.endswith(".java") else 'kotlin'
                    file_path = os.path.join(root, file)                    
                    self.parser.set_language(self.languages[language_key])
                    with open(file_path, 'rb') as f:
                        source_code = f.read()
                        tree = self.parser.parse(source_code)
                        self._walk_tree(tree.root_node, source_code, file_path, language_key, scope=[])                        

    def _walk_tree(self, node, source_code, file_path, language_key, scope):
        type_scope = tuple(scope)
        if node.type in ['package_declaration', 'package_directive']:  # Kotlin uses 'package_directive'
            package_name = source_code[node.start_byte:node.end_byte].decode('utf-8')
            scope.append(package_name)  # Adjust scope for package            
        elif node.type == 'class_declaration' or (language_key == 'kotlin' and node.type == 'class'):
            # Check if the 'name' child node exists before trying to access its attributes
            name_node = node.child_by_field_name('name')
            if name_node:
                class_name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8')                
                self.definitions[('class', class_name, type_scope, language_key)] = source_code[node.start_byte:node.end_byte].decode('utf-8')
                scope.append(class_name)  # Adjust scope for class
        elif node.type == 'method_declaration' or (language_key == 'kotlin' and node.type == 'function_declaration'):
            # Similarly, check if the 'name' child node exists
            name_node = node.child_by_field_name('name')
            if name_node:                
                method_name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                self.definitions[('method', method_name, type_scope, language_key)] = source_code[node.start_byte:node.end_byte].decode('utf-8')
        
        # Handling class instantiation (for both Java and Kotlin, adjust as needed)
        if node.type == 'new_expression' or (language_key == 'kotlin' and node.type == 'instantiation'):
            class_name_node = next((child for child in node.children if child.type in ['type_identifier', 'constructor_identifier']), None)
            if class_name_node:
                class_name = source_code[class_name_node.start_byte:class_name_node.end_byte].decode('utf-8')
                line_number = node.start_point[0] + 1                
                self.usages.setdefault(('class', class_name, type_scope, language_key), []).append(f"{file_path}:{line_number}")

        # Adjusted logic for method invocation, assuming you've identified the correct structure
        if node.type == 'call_expression' or node.type == 'method_invocation':
            method_name_node = next((child for child in node.children if child.type == 'identifier'), None)
            if method_name_node:
                method_name = source_code[method_name_node.start_byte:method_name_node.end_byte].decode('utf-8')
                line_number = node.start_point[0] + 1                
                self.usages.setdefault(('method', method_name, type_scope, language_key), []).append(f"{file_path}:{line_number}")

        # Recursively update scope and analyze children
        for child in node.children:
            self._walk_tree(child, source_code, file_path, language_key, scope[:])  # Pass a copy of the scope


    def get_definition(self, type_name, name, package=None, language='java'):
        # Attempt to find a definition with the exact package match first
        if package is not None:
            exact_key = ('class' if type_name == 'class' else 'method', name, (package,), language)
            exact_match = self.definitions.get(exact_key)
            if exact_match:
                print(f"Exact definition found for {type_name} {name} in package {package}")
                return exact_match

        # If exact match is not found or package is None, search for any match by name
        for key, definition in self.definitions.items():
            if key[1] == name and key[3] == language and (type_name == 'class' and key[0] == 'class' or type_name == 'method' and key[0] == 'method'):
                print(f"General definition found for {type_name} {name} regardless of package")
                return definition

        print(f"Definition not found for {type_name} {name}")
        return None        

    def find_usages(self, type_name, name, package=None, language='java'):
        # Attempt to find usages with the exact package match first
        if package is not None:
            exact_key = ('class' if type_name == 'class' else 'method', name, (package,), language)
            exact_match = self.usages.get(exact_key)
            if exact_match:
                print(f"Exact usages found for {type_name} {name} in package {package}")
                return exact_match

        # If exact match is not found or package is None, search for any usages by name
        general_matches = []
        for key, usages in self.usages.items():
            if key[1] == name and key[3] == language and (type_name == 'class' and key[0] == 'class' or type_name == 'method' and key[0] == 'method'):
                general_matches.extend(usages)
        
        if general_matches:
            print(f"General usages found for {type_name} {name} regardless of package")
            return general_matches

        print(f"Usages not found for {type_name} {name}")
        return None

# Example usage
if __name__ == '__main__':
    analyzer = SpringProjectParser('path/to/spring/project')
    definition = analyzer.get_definition('class', 'className', None, 'java')
    if definition:
        print(f"Definition found: {definition}")
    else:
        print("Definition not found.")

    usages = analyzer.find_usages('method', 'methodName', None, 'java')
    if usages:
        print(f"Usages found: {usages}")
    else:
        print("Usages not found.")
