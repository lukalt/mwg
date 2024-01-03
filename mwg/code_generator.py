from utils import StringBuilder


class CodeGenerator:
    """
    Utility class to write indented code to a string buffer
    """
    def __init__(self, includes: list, indention_step_spaces: int = 4, ident_level: int = 0):
        """
        Initializes a new code generator
        :param includes:
        :param indention_step_spaces: Number of spaces for indention step (default: 4 spaces)
        :param ident_level: Initial indention level
        """
        self.indention_step_spaces = indention_step_spaces
        self.indent_level = ident_level
        self.includes = includes

        self._builder = StringBuilder()

    def new_intended_block(self, runnable):
        """
        Invoke the provided function in an indented block
        :param runnable: Function that generates code
        """
        self.start_indent()
        runnable()
        self.close_indent()

    def start_indent(self):
        """
        Increases the current indention level
        """
        self.indent_level += self.indention_step_spaces

    def close_indent(self):
        """
        Decreases the current indention level
        """
        self.indent_level -= self.indention_step_spaces

    def include(self, import_str: str, sys: bool = True):
        """
        Adds a C new include statement
        :param import_str: The name of the header file
        :param sys: Whether to threat the include as a system-wide or local include
        """
        if sys:
            import_str = "<" + import_str + ">"
        else:
            import_str = "\"" + import_str + "\""
        if import_str not in self.includes:
            self.includes.append(import_str)

    def add_line(self, content):
        """
        Adds a new line to the string buffer. If the string contains multiple lines, only the first one will be
        indented.
        :param content:
        """
        self._builder.Add(" " * self.indent_level)
        self._builder.Add(content)
        self._builder.Add("\n")

    def add_multiline_indented(self, content):
        """
        Adds a multline-string to the buffer. Each line is indented
        :param content: Multiple content, separated by line feed
        """
        for l in content.split("\n"):
            self.add_line(l)

    def add_print_statement(self, content, *args):
        """
        Adds a print statement that prints a possible formatted string to the stdout
        :param content: formatter string
        :param args: args to the formatter
        """
        d = ", ".join(args)
        if d != "":
            d = ", " + d
        self.add_line(f"printf(\"{content}\\n\"{d});")

    def get_code(self):
        """
        Returns the current code buffer as a string
        :return: string representing the current string buffer
        """
        return str(self._builder)
