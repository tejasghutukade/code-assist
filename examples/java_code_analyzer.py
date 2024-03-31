from tree_sitter import Language, Parser
from typing import List, Dict

class JavaCodeAnalyzer:
    def __init__(self, language_lib_path='my-languages.so', language_name='java'):
        """
        Initializes the JavaCodeAnalyzer with the given Tree-sitter language library.

        :param language_lib_path: Path to the compiled Tree-sitter language library.
        :param language_name: Name of the language (should be 'java' for Java analysis).
        """
        self.language = Language(language_lib_path, language_name)
        self.parser = Parser()
        self.parser.set_language(self.language)

    def parse_source_code(self, source_code):    
        return self.parser.parse(bytes(source_code, "utf8"))

    def extract_java_class_and_method_names(self, java_code: str) -> dict:
        """
        Extracts class and method names from a given Java code string.

        :param java_code: A string containing Java source code.
        :return: A dictionary with class names as keys and a list of method names as values.
        """
        tree = self.parser.parse(bytes(java_code, 'utf8'))
        
        # This query finds class and method declarations in the AST.
        query = self.language.query("""
        (class_declaration name: (identifier) @class.name)
        (method_declaration name: (identifier) @method.name)
        """)

        captures = query.captures(tree.root_node)
        
        class_methods = {}
        for node, capture_name in captures:
            name_text = node.text.decode('utf8')
            
            if capture_name == 'class.name':
                # Initialize or update the class name entry with an empty list for methods.
                class_methods.setdefault(name_text, [])
            elif capture_name == 'method.name':
                # Find the closest class ancestor to the method to ensure correct class-method association.
                class_node = node.parent
                while class_node and class_node.type != 'class_declaration':
                    class_node = class_node.parent
                if class_node:
                    class_name = class_node.child_by_field_name('name').text.decode('utf8')
                    class_methods.setdefault(class_name, []).append(name_text)

        return class_methods

    def get_class_and_method_details(self, java_code: str) -> List[Dict[str, List[str]]]:
        """
        Processes Java source code to extract class and method names, returning a structured
        representation.

        :param java_code: A string containing Java source code.
        :return: A list of dictionaries, each with 'classname' and 'methods' keys.
        """
        # Extract class and method names using the existing method
        class_methods_dict = self.extract_java_class_and_method_names(java_code)

        # Transform the dictionary into the desired structured output
        structured_output = [
            {"class_names": class_name, "method_names": methods}
            for class_name, methods in class_methods_dict.items()
        ]

        return structured_output
    


    def find_definition(self, node, source_code, name_to_find, type_to_find):
        """
        Recursively searches for a class or method definition by name.
        
        :param node: The current node in the syntax tree.
        :param source_code: The entire source code as a string.
        :param name_to_find: The name of the class or method to find.
        :param type_to_find: Either 'class' or 'method' to specify what to find.
        """
        # Define the node types to look for based on what we're trying to find
        if type_to_find == 'class':
            node_type = 'class_declaration'
        elif type_to_find == 'method':
            node_type = 'method_declaration'
        else:
            raise ValueError("type_to_find must be 'class' or 'method'")
        
        if node.type == node_type:
            name_node = node.child_by_field_name('name')
            if name_node is not None:
                node_name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                if node_name == name_to_find:
                    # Print or process the node's text (here we simply print it)
                    print(f"Found {type_to_find}: {name_to_find}")
                    definition_text = source_code[node.start_byte:node.end_byte].decode('utf-8')
                    print(definition_text)
                    return
        
        # Recursively search in children
        for child in node.children:
            self.find_definition(child, source_code, name_to_find, type_to_find)