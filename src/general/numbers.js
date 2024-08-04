// Multipliers
const multipliers = {
    'dozen': 12,
    'hundred': 100,
    'thousand': 1e3,
    'million': 1e6,
    'billion': 1e9,
    'trillion': 1e12,
    'quadrillion': 1e15,
    'quintillion': 1e18,
    'sextillion': 1e21
};

const numbers = {
    'one': 1,
    'two': 2,
    'three': 3,
    'four': 4,
    'five': 5,
    'six': 6,
    'seven': 7,
    'eight': 8,
    'nine': 9,
    'ten': 10,
    'eleven': 11,
    'twelve': 12,
    'thirteen': 13,
    'fourteen': 14,
    'fifteen': 15,
    'sixteen': 16,
    'seventeen': 17,
    'eighteen': 18,
    'nineteen': 19,
    'twenty': 20,
    'thirty': 30,
    'forty': 40,
    'fifty': 50,
    'sixty': 60,
    'seventy': 70,
    'eighty': 80,
    'ninety': 90,
    'a': 1
};

class NumberWithUnit {
    constructor(number, unit = "") {
        this.number = number;
        this.unit = unit;
    }
    toString() {
        let string = "";
        if(this.number >= 1e3){
            for(let i=Object.keys(multipliers).length-1; i>=0; i--){
                let qual = Object.keys(multipliers)[i];
                if(this.number > multipliers[qual]){
                    string += (Math.round(this.number / multipliers[qual] * 10) / 10).toFixed(1) + " " + qual;
                    break;
                }
            }
        }else{
            string += this.number;
        }
        if(this.unit != null) string += " " + this.unit;
        // return `NumberWithUnit { number: ${this.number}, unit: '${this.unit}', readable: '${string}' }`;
        return string;
    }
}

function wordToNumber(words) {
    // Base numbers

    let total = 0;
    let currentNumber = 0;

    for (let i = 0; i < words.length; i++) {
        let word = words[i];
        if (!isNaN(word)) {
            currentNumber += parseInt(word);
        } else if (numbers[word] !== undefined) {
            currentNumber += numbers[word];
        } else if (i + 1 < words.length && numbers[words[i] + "-" + words[i + 1]]) {
            currentNumber += numbers[words[i] + "-" + words[i + 1]];
            i++; // Skip next word
        } else if (multipliers[word] !== undefined) {
            currentNumber *= multipliers[word];

            if (multipliers[word] > 100) {
                total += currentNumber;
                currentNumber = 0;
            }
        }
    }

    return total + currentNumber;
}

const parseNumber = (str) => {
    // Remove common qualifiers
    str = str.toLowerCase().replace(/about|approximately|roughly|close to|nearly|around|more or less|up to|at most|almost|circa|c\.|≈/g, '');
    str = str.replace(/,/g, '').trim();
    str = str.replace(/,/g, '').replace(/\*\*/g, '^').replace(/⨯/g, '*').replace(/×/g, '*').replace(/÷/g, '/').replace(/–/g, '-');

    // Split by range qualifiers
    let parts = str.split(/(?: to )/);

    if(parts.length == 1){
        parts = str.split(/(?<=\s|\d)-(?=\s|\d)/);
        if(parts.length == 3){
            parts = [parts[0] + "-" + parts[1], parts[2]];
        }else if(parts.length == 4){
            parts = [parts[0] + "-" + parts[1], parts[2] + "-" + parts[3]];
        }
    }else if(parts.length > 2){
        return null;
    }

    // Process each part
    const results = parts.map(part => {
        // Extract possible number words and process
        let wordParts = (" "+part+" ").match(/(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|trillion|quadrillion| and | a )/g);
        
        if (wordParts && wordParts.length > 0) {
            wordParts = (" "+part+" ").match(/([\d]+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|trillion|quadrillion| and | a )/g);
            const numberVal = wordToNumber(wordParts);
            const nonNumberParts = part.replace(new RegExp(wordParts.join('|'), 'g'), '').trim();

            if (nonNumberParts) {
                return new NumberWithUnit(numberVal, nonNumberParts);
            }
            return numberVal;
        }

        // If not worded numbers, directly evaluate math or return part
        const regex = /\s*([\s-?\d+.\/*\^()]*)?\s*([a-z\-%^\(\) ]*)?/i;
        const match = part.match(regex);

        if (!match || match[1] === undefined){
            const evaluated = safeEval(part.trim());
            if (typeof evaluated === 'number') return evaluated;
            return new NumberWithUnit(0, part.trim());
        }

        const expression = match[1].trim().replace(/\s+/g, '').replace(/\^/g, '**');
        const result = safeEval(expression);
        const detectedUnit = match[2] || '';

        if(detectedUnit){
            return new NumberWithUnit(result, detectedUnit);
        }else{
            return result;
        }

    });

    if(results.length > 1 && typeof results[0] == "number" && typeof results[1] == "object"){
        return [new NumberWithUnit(results[0], results[1].unit), results[1]];
    }

    return results;
};

const safeEval = (str) => {
    try {
        return eval(str);
    } catch (e) {
        return null;
    }
};

function roundToThree(num){
    // Round the number to the nearest thousandth
    let roundedNum = Math.round(num * 1000) / 1000;

    // Convert to string and remove trailing zeros
    let str = roundedNum.toFixed(3);

    // Use a regular expression to remove trailing zeros after the decimal point
    str = str.replace(/(\.\d*?[1-9])0+|\.0*$/, '$1');

    return str;
}

function printNumber(number){
    // Return infinites as is
    if(number == "infinity" || number == "-infinity"){
        return number;
    // Return numbers between -0.001 and 0.001 as is
    }else if(Math.abs(number) > 1e-3 && Math.abs(number) < 1){
        return "" + number;
    // Return zero as is
    }else if(number == 0.0){
        return "0";
    // Return small numbers in scientific notation
    }else if(Math.abs(number) < 1){
        return number.toExponential();
    // For numbers less than 1 million, return with commas
    }else if(Math.abs(number) >= 1 && Math.abs(number) < 1e6){
        let sign = number < 0 ? "-" : "";
        number = Math.abs(number);
        let integer_part = Math.floor(Math.abs(number));
        let decimal_part = roundToThree(Math.abs(number) - integer_part);
        if(decimal_part > 0){
            return sign + integer_part.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") + decimal_part.toString().substr(1);
        }else{
            return sign + integer_part.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        }
    // Write 'million', 'billion', etc. for numbers greater than 1 million
    }else{
        const multipliers = ['thousand', 'million', 'billion', 'trillion', 'quadrillion', 'quintillion', 'sextillion', 'septillion', 'octillion', 'nonillion', 'decillion', 'undecillion', 'duodecillion', 'tredecillion', 'quattuordecillion', 'quindecillion', 'sexdecillion', 'septendecillion', 'octodecillion', 'novemdecillion', 'vigintillion', null];
        for(let i=multipliers.length-1; i>=0; i--){
            let qual = multipliers[i];
            if(Math.abs(number) >= Math.pow(10, 3*i+3)){
                if (qual == null) {
                    return number.toExponential();
                }
                return roundToThree(number / Math.pow(10, 3*i+3)) + " " + qual + " (" + number.toExponential() + ")";
            }
        }
    }
}

function printNumberOrIntervalWithUnits(number, unit, approx=false){
    let string = "";
    if(approx)
        string = "approximately ";
    if(Array.isArray(number)){
        if(number[0] == "-infinity" || number[0] == 0 || number[0] === undefined || number[0] == null){
            string = string + "less than " + printNumber(number[1]);
        }else if(number[1] == "infinity" || number[1] === undefined || number[1] == null){
            string = string + "over " + printNumber(number[0]);
        }else{
            string = string + "between " + printNumber(number[0]) + " and " + printNumber(number[1]);
        }
    }else{
        string = string + printNumber(number);
    }
    if(unit != null){
        string = string + " " + unit;
    }
    return string;
}


export { NumberWithUnit, parseNumber, printNumberOrIntervalWithUnits };