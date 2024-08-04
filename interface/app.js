document.addEventListener('DOMContentLoaded', () => {
  let allQuestions = [];
  let lastQuestionsIndices = [];
  let currentQuestionIndex = 0;

  // const topicElement = document.getElementById('topic');
  const descriptionElement = document.getElementById('description');
  const unitElement = document.getElementById('unit');
  const dateElement = document.getElementById('date');
  const userAnswerElement = document.getElementById('user-answer');
  const submitBtn = document.getElementById('submit-btn');
  const resultContainer = document.getElementById('result-container');
  const foundExcerptElement = document.getElementById('found-excerpt');
  const nextQuestionBtn = document.getElementById('next-question-btn');
  const inputContainer = document.getElementById('input-container');
  const canvas = document.getElementById('visualization-canvas');
  const context = canvas.getContext('2d');

  // Seeding
  let seed = null;
  document.getElementById('shareButton').addEventListener('click', function() {
    if (!seed) {
      return;
    }
  
    // Get the current URL
    let currentUrl = new URL(window.location.href);
  
    // Check if the search parameter already exists
    if (currentUrl.searchParams.has('s')) {
        // Update the existing search parameter
        currentUrl.searchParams.set('s', seed);
    } else {
        // Add the search parameter
        currentUrl.searchParams.append('s', seed);
    }
  
    // Get the modified URL as a string
    const modifiedUrl = currentUrl.toString();
  
    // // Change the current URL without refreshing the page
    // history.pushState(null, '', modifiedUrl);
  
    // Copy the modified URL to the clipboard
    navigator.clipboard.writeText(modifiedUrl).then(function() {
        console.log('URL copied to clipboard');
    }).catch(function(err) {
        alert('Failed to copy ' + modifiedUrl + ' : ', err);
    });
  });

  // Questions
  fetch('data.json.gz', {
    headers: {
      'Content-Encoding': 'gzip'
    }
  })
  .then(response => response.arrayBuffer())
  .then(buffer => {
    // Decompress the data using pako
    const decompressedData = pako.inflate(new Uint8Array(buffer), { to: 'string' });
    const jsonData = JSON.parse(decompressedData);
    allQuestions = jsonData;
    getNewQuestion();
  })
  .catch(error => {
    console.error('Error fetching or decompressing data:', error);
  });


  function getNewQuestion() {
    if (allQuestions.length === 0) {
      return null;
    }
    if(!seed)
      seed = getSeedFromURL() || generateSeed();
    else{
      seed = generateSeed(mulberry32(decodeSeed(seed)));
    }

    const rng = mulberry32(decodeSeed(seed));

    currentQuestionIndex = null;
    while (currentQuestionIndex === null) {
      const randomIndex = Math.floor(rng() * allQuestions.length);
      if (!lastQuestionsIndices.includes(randomIndex)) {
        currentQuestionIndex = randomIndex;
        lastQuestionsIndices.push(randomIndex);
        if (lastQuestionsIndices.length > 10) {
          lastQuestionsIndices.shift();
        }
      }
    }

    displayQuestion();
  }

  function displayQuestion() {
    const question = allQuestions[currentQuestionIndex];
    // topicElement.textContent = question.topic;
    descriptionElement.textContent = question.description[0];
    dateElement.innerHTML = question.description[1] ? `${question.description[1]}` : '';
    unitElement.innerHTML = question.description[2] ? `${question.description[2]}` : '';
    userAnswerElement.value = '';
    inputContainer.style.display = 'block';
    resultContainer.style.display = 'none';
  }

  async function handleSubmit() {
    const userAnswer = parseNumberString(userAnswerElement.value);
    if (userAnswer === null) {
      userAnswerElement.classList.add('error');
      return;
    }else{
      userAnswerElement.classList.remove('error');
    }
    const question = allQuestions[currentQuestionIndex];
    const correctAnswer = question.answer;
    foundExcerptElement.textContent = question.excerpt;
    inputContainer.style.display = 'none';
    resultContainer.style.display = 'block';

    showVisualization(userAnswer, correctAnswer);
  }

  function toFixed_leq(x, n) {
    let s = x.toFixed(n);
    // Remove trailing zeros
    s = s.replace(/(\.\d*?[1-9])0+|\.0*$/, '$1');
    return s;
  }

  function displayNumber(number, options = { exact: true, longForm: true }) {
    const SHORT_SYMBOL = ["", "k", "M", "B", "T", "Q", "Qn"];
    const LONG_SYMBOL = ["", "thousand", "million", "billion", "trillion", "quadrillion", "quintillion"];

    function abbreviateNumber(number, longForm, exact) {
        let tier = Math.log10(Math.abs(number)) / 3 | 0;

        if (tier === 0) return number.toLocaleString();

        let first_line = "";
        if (tier < SHORT_SYMBOL.length) {
          const suffix = longForm ? LONG_SYMBOL[tier] : SHORT_SYMBOL[tier];
          const scale = Math.pow(10, tier * 3);

          const scaled = number / scale;

          if (!exact) {
            const scaled_string = toFixed_leq(scaled, 1);
            first_line = scaled_string + " " + suffix + "\n";
          }else{
            // Should we return the number as is?
            if(number >= 1e10)
              first_line = scaled + " " + suffix + "\n";
          }
        }

        let second_line = "";
        if(exact && number < 1e10)
          second_line = number.toLocaleString();
        else{
          let exponent = Math.floor(Math.log10(Math.abs(number)));
          let mantissa = (number * Math.pow(10, -exponent));
          mantissa = Math.round(mantissa * 1000000000) / 1000000000;
          if(!exact)
            mantissa = toFixed_leq(mantissa, 1);
          if(mantissa == 1)
            second_line = `10^${exponent}`;
          else if(mantissa == -1)
            second_line = `-10^${exponent}`;
          else
            second_line = `${mantissa} x 10^${exponent}`;
        }

        return first_line + second_line;
    }

    if (number === 0) {
        return '0';
    } else if (Math.abs(number) < 1e-3) {
        let exponent = Math.floor(Math.log10(Math.abs(number)));
        let mantissa = toFixed_leq(number * Math.pow(10, -exponent), 1);
        return `${mantissa} x 10^${exponent}`;
    } else if (Math.abs(number) >= 1e6) {
        return abbreviateNumber(number, options.longForm, options.exact);
    } else if (Math.abs(number) >= 1e3) {
        return number.toLocaleString();
    } else {
        return toFixed_leq(number, 3);
    }
  }

  function calculateRoundLogTicks(maxValue, numTicks, minDistance=0) {
    const logBase = 10;

    let maxLog = 0;
    while (customScale(Math.pow(logBase, maxLog)) < maxValue) {
      maxLog++;
    }
    maxLog--;

    let allowedLeadingDigits = [];
    if (maxLog <= 4) {
      allowedLeadingDigits = [1,2,3,4,5,6,7,8,9];
    } else if (maxLog <= 8) {
      allowedLeadingDigits = [1,2,5];
    } else if(maxLog <= 12) {
      allowedLeadingDigits = [1,3];
    } else {
      allowedLeadingDigits = [1];
    }

    let currentLog = maxLog;
    let currentLeadingDigitIndex = allowedLeadingDigits.length - 1;

    let ticks = [];
    let i = 0;
    while(i < numTicks) {
      const tickValue = allowedLeadingDigits[currentLeadingDigitIndex] * Math.pow(logBase, currentLog);
      const scaledValue = customScale(tickValue);
      if (scaledValue <= maxValue) {
        if(ticks.length == 0 || (customScale(ticks[ticks.length - 1]) - scaledValue > minDistance &&  scaledValue - customScale(0) > minDistance))
          ticks.push(tickValue);
        i++;
      }

      currentLeadingDigitIndex--;
      if(currentLeadingDigitIndex < 0) {
        currentLeadingDigitIndex = allowedLeadingDigits.length - 1;
        currentLog--;
      }
    }
    ticks.push(0);
    return ticks.reverse();
  }

  function customScale(x, k=1000.0) {
    let sign = x < 0 ? -1 : 1;
    x = Math.abs(x);
    return sign*(Math.log(k+x) - Math.log(k));
  }

  function showVisualization(userAnswer, correctAnswer) {
    const ideal_width = document.body.clientWidth > 800 ? 800 : 400;
    const ideal_height = 100;
    const ideal_padding = 10;
    const ideal_x_offset = 50;

    let width = ideal_width;
    let height = ideal_height;
    let padding = ideal_padding;
    let global_scale = 1.0;
    let x_offset = ideal_x_offset;
    let effective_width = width - 2 * x_offset;

    function resizeCanvas() {
      const bodyStyle = window.getComputedStyle(document.body);
      width = Math.min(document.body.clientWidth, ideal_width);
      global_scale = (width / ideal_width);
      height = ideal_height * global_scale;
      padding = ideal_padding * global_scale;
      x_offset = ideal_x_offset * global_scale;
      effective_width = width - 2 * x_offset;

      const dpi = window.devicePixelRatio;
      canvas.width = width * dpi;
      canvas.height = height * dpi;
      canvas.getContext('2d').scale(dpi, dpi);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
    }

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    const answers = typeof correctAnswer == 'object' ? [userAnswer, ...correctAnswer] : [userAnswer, correctAnswer];
    const colors = typeof correctAnswer == 'object' ? ['red', 'green', 'green'] : ['red', 'green'];
    let answersX = [];
    for(let i = 0; i < answers.length; i++) {
      answersX[i] = customScale(answers[i]);
    }
    const _minAnswerX = Math.min(...answersX);
    const _maxAnswerX = Math.max(...answersX);

    let _origMaxX, _origMinX;
    if(_minAnswerX > 0){
      _origMaxX = _minAnswerX + _maxAnswerX;
      _origMinX = 0.0;
    }else if(_maxAnswerX < 0){
      _origMinX = _maxAnswerX + _minAnswerX;
      _origMaxX = 0.0;
    }else{
      _origMinX = _minAnswerX;
      _origMaxX = _maxAnswerX;
    }

    // Animate zoom
    const duration = 3000;
    const startTime = performance.now();

    function transition(x) {
      return Math.sin((x * Math.PI) / 2);
    }

    function animate() {
      const currentTime = performance.now();
      const elapsedTime = currentTime - startTime;
      const t = transition(Math.min(elapsedTime / duration, 1));

      const initialZoom = 10.0
      let origMaxX = _origMaxX > 0 ? customScale(initialZoom) + t * (_origMaxX - customScale(initialZoom)) : 0.0;
      let origMinX = _origMinX < 0 ? -customScale(initialZoom)  + t * (_origMinX + customScale(initialZoom)) : 0.0;

      // Draw X-axis ticks
      const numTicks = 40;
      const tickScale = 0.04 * Math.max(Math.abs(_origMaxX), Math.abs(_origMinX));
      let tickValues = calculateRoundLogTicks(origMaxX - origMinX, numTicks, tickScale);
      if(origMinX < 0){
        // Copy the positive ticks as negative ticks
        tickValues = tickValues.map(x => -x).reverse().slice(0,-1).concat(tickValues);
      }

      const fontSize = 10*global_scale;

      context.clearRect(0, 0, width, height);
      context.save();

      // Redraw line
      context.beginPath();
      context.moveTo(0, height / 2);
      context.lineTo(width, height / 2);
      context.strokeStyle = 'black';
      context.lineWidth = 2;
      context.stroke();

      // Redraw X-axis ticks
      let lastX = -Infinity;
      for (let i = 0; i < tickValues.length; i++) {
        const tickValue = tickValues[i];
        const x = effective_width * (customScale(tickValue) - origMinX) / (origMaxX - origMinX);

        // Draw tick line
        context.beginPath();
        context.moveTo(x_offset + x, height / 2 - padding);
        context.lineTo(x_offset + x, height / 2 + padding);
        context.strokeStyle = 'black';
        context.lineWidth = 1;
        context.stroke();
        
        context.font = fontSize.toFixed(1) + 'px Arial';
        context.fillStyle = 'black';
        context.textAlign = 'center';

        // Draw tick label
        const labelText = displayNumber(tickValue, { exact: false, longForm: false });
        const lines = labelText.split('\n');
        
        let tickLabelWidth = 0;
        const lineHeight = fontSize;
        for (let j = 0; j < lines.length; j++) {
            // Draw each line
            let w = context.measureText(lines[j]).width;
            tickLabelWidth = Math.max(tickLabelWidth, w);
        }
        
        if (x - tickLabelWidth / 2 > lastX) {
          for (let j = 0; j < lines.length; j++) {
              // Draw each line
              context.fillText(lines[j], x_offset + x, height / 2 + 2 * padding + (j * lineHeight));
          }
          lastX = x + tickLabelWidth / 2;
        }
      }

      for(let i = 0; i < answers.length; i++) {
        // Redraw circle of answer
        let x = effective_width * (answersX[i] - origMinX) / (origMaxX - origMinX);
        context.beginPath();
        context.arc(x_offset + x, height / 2, 5, 0, 2 * Math.PI);
        context.fillStyle = colors[i];
        context.fill();

        // Redraw value text of answer
        context.font = fontSize.toFixed(1) + 'px Manrope';
        context.fillStyle = colors[i];
        context.textAlign = 'center';

        const labelText = displayNumber(answers[i]);
        const lines = labelText.split('\n');
        const lineHeight = -fontSize;
        for (let j = lines.length-1; j >= 0; j--) {
          context.fillText(lines[j], x_offset + x, height / 2 - 2 * padding + (j * lineHeight));
        }
      }

      if(answers.length > 2) {
        // Draw green line
        context.beginPath();
        context.moveTo(x_offset + effective_width * (answersX[1] - origMinX) / (origMaxX - origMinX), height / 2);
        context.lineTo(x_offset + effective_width * (answersX[2] - origMinX) / (origMaxX - origMinX), height / 2);
        context.strokeStyle = colors[1];
        context.lineWidth = 6;
        context.stroke();
      }

      context.restore();

      if (t < 1) {
        requestAnimationFrame(animate);
      }
    }

    requestAnimationFrame(animate);
  }

  function handleNextQuestion() {
    getNewQuestion();
  }

  submitBtn.addEventListener('click', handleSubmit);
  nextQuestionBtn.addEventListener('click', handleNextQuestion);
});


//
// Seeds and sharing
//

function mulberry32(seed) {
  return function() {
    let t = seed += 0x6D2B79F5;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

function getSeedFromURL() {
  // Get the current URL
  let currentUrl = new URL(window.location.href);

  let seed = null;

  // Check if the search parameter already exists
  if (currentUrl.searchParams.has('s')) {
      // Get seed and remove the existing search parameter
      seed = currentUrl.searchParams.get('s')
      currentUrl.searchParams.delete('s');
  } else {
      seed = generateSeed();
  }

  // Get the modified URL as a string
  const modifiedUrl = currentUrl.toString();

  // Change the current URL without refreshing the page
  history.pushState(null, '', modifiedUrl);

  return seed;
}

function generateSeed(rng=Math.random) {
  const consonants = 'bcdfghjklmnpqrstvwxyz'.toUpperCase();
  const vowels = 'aeiou'.toUpperCase();
  let seed = '';
  for (let i = 0; i < 12; i++) {
    if (i % 2 === 0) {
      seed += consonants.charAt(Math.floor(rng() * consonants.length));
    } else {
      seed += vowels.charAt(Math.floor(rng() * vowels.length));
    }
  }
  return seed;
}

function decodeSeed(seed){
  const consonants = 'bcdfghjklmnpqrstvwxyz'.toUpperCase();
  const vowels = 'aeiou'.toUpperCase();
  let decodedSeed = 0;
  for (let i = 0; i < seed.length; i++) {
    if (i % 2 === 0) {
      decodedSeed = decodedSeed*consonants.length + consonants.indexOf(seed.charAt(i));
    } else {
      decodedSeed = decodedSeed*vowels.length + vowels.indexOf(seed.charAt(i));
    }
  }
  return decodedSeed;
}

function encodeSeed(decodedSeed){
  const consonants = 'bcdfghjklmnpqrstvwxyz'.toUpperCase();
  const vowels = 'aeiou'.toUpperCase();
  let seed = '';
  while (decodedSeed > 0) {
    if (seed.length % 2 !== 0) {
      seed = consonants.charAt(decodedSeed % consonants.length) + seed;
      decodedSeed = Math.floor(decodedSeed / consonants.length);
    } else {
      seed = vowels.charAt(decodedSeed % vowels.length) + seed;
      decodedSeed = Math.floor(decodedSeed / vowels.length);
    }
  }
  return seed;
}

//
// Parsing numbers
//

function parseNumberString(input) {
  // Define multipliers
  const multipliers = {
      "hundred": 100,
      "thousand": 1000,
      "million": 1e6,
      "billion": 1e9,
      "trillion": 1e12,
      'quadrillion': 1e15,
      'quintillion': 1e18,
      'sextillion': 1e21,
      'septillion': 1e24,
      'octillion': 1e27,
      'nonillion': 1e30,
      'decillion': 1e33,
      'undecillion': 1e36,
      'duodecillion': 1e39,
      'tredecillion': 1e42,
      'quattuordecillion': 1e45,
      'quindecillion': 1e48,
      'sexdecillion': 1e51,
      'septendecillion': 1e54,
      'octodecillion': 1e57,
      'novemdecillion': 1e60,
      'vigintillion': 63
  };

  // Remove whitespace from input
  input = input.trim();

  // Check for basic number
  if (!isNaN(input)) {
      return parseFloat(input);
  }

  // Check for XeN format
  let xeNMatch = input.match(/^(\d+(\.\d+)?)e(\d+)$/i);
  if (xeNMatch) {
      let base = parseFloat(xeNMatch[1]);
      let exponent = parseInt(xeNMatch[3]);
      return base * Math.pow(10, exponent);
  }

  // Check for A^N format
  let aNMatch = input.match(/^(\d+(\.\d+)?)\^(\d+)$/);
  if (aNMatch) {
      let base = parseFloat(aNMatch[1]);
      let exponent = parseInt(aNMatch[3]);
      return Math.pow(base, exponent);
  }

  // Check for C*A^N format
  let cANMatch = input.match(/^(\d+(\.\d+)?)\*(\d+(\.\d+)?)\^(\d+)$/);
  if (cANMatch) {
      let coefficient = parseFloat(cANMatch[1]);
      let base = parseFloat(cANMatch[3]);
      let exponent = parseInt(cANMatch[5]);
      return coefficient * Math.pow(base, exponent);
  }

  // Check for number with multiplier
  let numberMultiplierMatch = input.match(/^(\d+(\.\d+)?)\s+(\w+)$/);
  if (numberMultiplierMatch) {
      let number = parseFloat(numberMultiplierMatch[1]);
      let multiplier = numberMultiplierMatch[3].toLowerCase();
      if (multipliers[multiplier] !== undefined) {
          return number * multipliers[multiplier];
      } else {
          return null;
      }
  }

  return null;
}