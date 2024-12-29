import json

def complete_truncated_json(input_str, multiple_jsons=False):
    if not input_str:
        return None
    input_str = input_str.strip()
    
    if multiple_jsons:
        input_str = "[" + input_str

    stack = []
    inside_string = False

    i = 0
    while i < len(input_str):
        char = input_str[i]
        
        if char == '"' and (i == 0 or input_str[i - 1] != '\\'):
            inside_string = not inside_string
        
        if not inside_string:
            if char == '{' or char == '[':
                stack.append(char)
            elif char == ':':
                stack.pop()
                stack.append(":")
            elif char == ',' and stack[-1] == ':':
                stack.pop()
                stack.append("{")
            elif char == '}' and stack[-1] == ':':
                stack.pop()
                if len(stack) == 1 and multiple_jsons:
                    input_str = input_str[:i+1] + "," + input_str[i+1:]
            elif char == ']' and stack[-1] == '[':
                stack.pop()
                if len(stack) == 1 and multiple_jsons:
                    input_str = input_str[:i+1] + "," + input_str[i+1:]
        
        i += 1

    while True:
        try:
            parsed_json = json.loads(input_str)
            remove_incomplete(parsed_json)
            return parsed_json
        except json.JSONDecodeError:
            if inside_string:
                input_str += '_unfinished_"'
                inside_string = False
                continue
            
            if not stack:
                break
            
            last_opened = stack[-1]
            
            if last_opened == ':':
                if input_str.endswith(':'):
                    input_str += '"_unfinished_"}'
                elif input_str.endswith(','):
                    input_str = input_str[:-1] + '}'
                else:
                    input_str += '}'
                stack.pop()
            elif last_opened == '{':
                if input_str.endswith('{'):
                    input_str += '"_unfinished_": "_unfinished_"}'
                elif input_str.endswith(','):
                    input_str = input_str[:-1] + '}'
                else:
                    input_str += ': "_unfinished_"}'
                stack.pop()
            elif last_opened == '[':
                if input_str.endswith('['):
                    input_str += '"_unfinished_"]'
                elif input_str.endswith(','):
                    input_str = input_str[:-1] + ']'
                else:
                    input_str += ']'
                stack.pop()

    return None


def remove_incomplete(data):
    if isinstance(data, list):
        if len(data) > 0 and is_incomplete(data[-1]):
            data.pop()
    elif isinstance(data, dict):
        last_key = list(data.keys())[-1]
        if is_incomplete(last_key) or is_incomplete(data[last_key]):
            del data[last_key]
        else:
            remove_incomplete(data[last_key])


def is_incomplete(value):
    if isinstance(value, str):
        return value.endswith('_unfinished_')
    elif isinstance(value, dict):
        for key, val in value.items():
            if is_incomplete(key) or is_incomplete(val):
                return True
    return False
