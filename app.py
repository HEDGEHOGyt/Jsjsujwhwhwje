import re
import logging
from flask import Flask, request, jsonify

class SimpleLangInterpreter:
    def __init__(self):
        self.variables = {}
        self.functions = {}
        self.return_value = None

    def parse_and_execute(self, code):
        lines = code.split('\n')
        i = 0
        output = ""
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith('#'):  # поддержка комментариев
                i += 1
                continue
            if 'print' in line:
                output += self.handle_print(line) + "\n"
            elif 'input' in line:
                output += "Input command is not supported in web interface.\n"
            elif '=' in line:
                self.handle_assignment(line)
            elif 'if' in line:
                i, res = self.handle_if(lines, i)
                output += res
                continue
            elif 'while' in line:
                i, res = self.handle_while(lines, i)
                output += res
                continue
            elif 'def' in line:
                i = self.handle_def(lines, i)
                continue
            elif re.match(r'\w+\s*\(.*\)', line):  # вызов функции
                output += self.handle_function_call(line) + "\n"
            elif 'return' in line:
                self.handle_return(line)
                return output
            elif 'import' in line:
                output += "Import command is not supported in web interface.\n"
            else:
                output += f"Unknown command: {line}\n"
            i += 1
        return output

    def handle_print(self, line):
        match = re.match(r'print\s*\(([^)]+)\)', line)
        if match:
            expr = match.group(1).strip()
            value = self.evaluate_expression(expr)
            if value is not None:
                return str(value)
        else:
            return "Syntax error in print statement"

    def handle_input(self, line):
        match = re.match(r'(\w+)\s*=\s*input\s*\(([^)]*)\)', line)
        if match:
            var_name = match.group(1).strip()
            prompt = match.group(2).strip().strip('"')
            self.variables[var_name] = input(prompt)
        else:
            return "Syntax error in input statement"

    def handle_assignment(self, line):
        match = re.match(r'(\w+)\s*=\s*(.+)', line)
        if match:
            var_name = match.group(1).strip()
            value = match.group(2).strip()
            self.variables[var_name] = self.evaluate_expression(value)
        else:
            return "Syntax error in assignment statement"

    def handle_if(self, lines, index):
        condition_line = lines[index].strip()
        condition = re.match(r'if\s*\(([^)]+)\)', condition_line).group(1).strip()
        end_index = index + 1

        while end_index < len(lines) and lines[end_index].strip() != 'endif':
            end_index += 1

        output = ""
        if self.evaluate_expression(condition):
            output = self.parse_and_execute('\n'.join(lines[index + 1:end_index]))
        return end_index, output

    def handle_while(self, lines, index):
        condition_line = lines[index].strip()
        condition = re.match(r'while\s*\(([^)]+)\)', condition_line).group(1).strip()
        end_index = index + 1

        while end_index < len(lines) and lines[end_index].strip() != 'endwhile':
            end_index += 1

        output = ""
        while self.evaluate_expression(condition):
            output += self.parse_and_execute('\n'.join(lines[index + 1:end_index]))
        return end_index, output

    def handle_def(self, lines, index):
        def_line = lines[index].strip()
        match = re.match(r'def\s+(\w+)\s*\(([^)]*)\)', def_line)
        if match:
            func_name = match.group(1).strip()
            params = [param.strip() for param in match.group(2).split(',') if param.strip()]
            end_index = index + 1

            while end_index < len(lines) and lines[end_index].strip() != 'enddef':
                end_index += 1

            self.functions[func_name] = {
                'params': params,
                'body': lines[index + 1:end_index]
            }
        return end_index

    def handle_function_call(self, line):
        match = re.match(r'(\w+)\s*\(([^)]*)\)', line)
        if match:
            func_name = match.group(1).strip()
            args = [self.evaluate_expression(arg.strip()) for arg in match.group(2).split(',')]
            if func_name in self.functions:
                func = self.functions[func_name]
                if len(args) == len(func['params']):
                    saved_variables = self.variables.copy()
                    self.variables.update(zip(func['params'], args))
                    self.return_value = None
                    self.parse_and_execute('\n'.join(func['body']))
                    self.variables = saved_variables
                    return str(self.return_value)
                else:
                    return f"Function {func_name} expects {len(func['params'])} arguments, got {len(args)}"
            else:
                return f"Undefined function: {func_name}"

    def handle_return(self, line):
        match = re.match(r'return\s+(.+)', line)
        if match:
            self.return_value = self.evaluate_expression(match.group(1).strip())

    def handle_import(self, line):
        match = re.match(r'import\s+(.+)', line)
        if match:
            filename = match.group(1).strip().strip('"')
            try:
                with open(filename, 'r') as file:
                    code = file.read()
                    self.parse_and_execute(code)
            except FileNotFoundError:
                return f"File not found: {filename}"

    def evaluate_expression(self, expr):
        if expr.isdigit():
            return int(expr)
        elif expr in self.variables:
            return self.variables[expr]
        else:
            try:
                return eval(expr, {}, self.variables)
            except Exception as e:
                return f"Error evaluating expression: {expr}"

# Initialize interpreter
interpreter = SimpleLangInterpreter()

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SimpleLang Interpreter</title>
    </head>
    <body>
        <h1>SimpleLang Interpreter</h1>
        <form id="codeForm">
            <textarea id="codeInput" rows="10" cols="50"></textarea><br>
            <button type="button" onclick="executeCode()">Execute</button>
        </form>
        <h2>Output:</h2>
        <pre id="output"></pre>

        <script>
            async function executeCode() {
                const code = document.getElementById('codeInput').value;
                const response = await fetch('/execute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ code }),
                });
                const result = await response.json();
                document.getElementById('output').innerText = result.output;
            }
        </script>
    </body>
    </html>
    """

@app.route('/execute', methods=['POST'])
def execute():
    data = request.get_json()
    code = data.get('code', '')
    result = interpreter.parse_and_execute(code)
    return jsonify({'output': result})

if __name__ == '__main__':
    app.run(debug=True)
