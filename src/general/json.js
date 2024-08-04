function completeTruncatedJSON(inputStr, multiple_jsons=false) {
    if (!inputStr) return null;
    inputStr = inputStr.trim();
    if(multiple_jsons) inputStr = "[" + inputStr;

    let stack = [];
    let insideString = false;

    for (let i=0; i<inputStr.length; i++) {
        let char = inputStr[i];
        if (char === '"' && ((i > 0 && inputStr[i - 1] !== '\\') || (i >1 && inputStr[i - 2] === '\\'))) {
            insideString = !insideString;
        }

        if (!insideString) {
            if (char === '{' || char === '[') {
                stack.push(char);
            } else if (char === ':') {
                stack.pop();
                stack.push(":");
            } else if (char === ',' && stack[stack.length-1] === ':') {
                stack.pop();
                stack.push("{");
            } else if (char === '}' && stack[stack.length - 1] === ':') {
                stack.pop();
                if(stack.length == 1 && multiple_jsons){
                    inputStr = inputStr.slice(0, i+1) + "," + inputStr.slice(i+1);
                }
            } else if (char === ']' && stack[stack.length - 1] === '[') {
                stack.pop();
                if(stack.length == 1 && multiple_jsons){
                    inputStr = inputStr.slice(0, i+1) + "," + inputStr.slice(i+1);
                }
            }
        }
    }

    while (true) {
        try {
            let json = JSON.parse(inputStr);
            removeIncomplete(json);
            return json;
        } catch (e) {
            if (insideString) {
                inputStr += '_unfinished_"';
                insideString = false;
                continue;
            }

            if (stack.length === 0) {
                break;
            }

            let lastOpened = stack[stack.length - 1];

            if (lastOpened === ':') {
                if (inputStr.endsWith(':')) {
                    inputStr += '"_unfinished_"}';
                } else if (inputStr.endsWith(',')) {
                    inputStr = inputStr.slice(0, -1) + '}';
                } else {
                    inputStr += '}';
                }
                stack.pop();
            } else if (lastOpened === '{') {
                if (inputStr.endsWith('{')) {
                    inputStr += '"_unfinished_": "_unfinished_"}';
                } else if (inputStr.endsWith(',')) {
                    inputStr = inputStr.slice(0, -1) + '}';
                } else {
                    inputStr += ': "_unfinished_"}';
                }
                stack.pop();
            } else if (lastOpened === '[') {
                if (inputStr.endsWith('[')) {
                    inputStr += '"_unfinished_"]';
                } else if (inputStr.endsWith(',')) {
                    inputStr = inputStr.slice(0, -1) + ']';
                } else {
                    inputStr += ']';
                }
                stack.pop();
            }
        }
    }

    return null;
}

function removeIncomplete(data) {
    if (Array.isArray(data)) {
        let i = data.length - 1;
        if (isIncomplete(data[i])) {
            data.splice(i, 1);
            i--;  // adjust index after splicing
        }  
    } else if (typeof data === 'object' && data !== null) {
        let key = Object.keys(data)[Object.keys(data).length - 1]
        if (isIncomplete(key) || isIncomplete(data[key])) {
            delete data[key];
        } else {
            removeIncomplete(data[key])
        }
    }
}

function isIncomplete(value) {
    if (typeof value === 'string') {
        // Check for trailing spaces or if it's a placeholder value
        return value.endsWith('_unfinished_');
    } else if (!Array.isArray(value) && typeof value === 'object') {
        if (value === null) return false;

        for (let key in value) {
            if (isIncomplete(key) || isIncomplete(value[key])){
                return true;
            } 
        }
    }
    return false;
}


export { completeTruncatedJSON };