let displayQuestion = function (question) {};
let displayWaitingForAnswersScreen = function () {};
let displayFeedbackScreen = function () {};
let displayError = function (message) {};

document.addEventListener("DOMContentLoaded", () => {
  // const topicElement = document.getElementById('topic');
  const loadingContainer = document.getElementById("loading-container");
  const questionContainer = document.getElementById("question-container");
  const descriptionElement = document.getElementById("description");
  const unitElement = document.getElementById("unit");
  const dateElement = document.getElementById("date");
  const userAnswerElement = document.getElementById("user-answer");
  const submitBtn = document.getElementById("submit-btn");
  const watingForAnswersContainer = document.getElementById(
    "waiting-for-answers-container"
  );
  const resultContainer = document.getElementById("result-container");
  const foundExcerptElement = document.getElementById("found-excerpt");
  const nextQuestionBtn = document.getElementById("next-question-btn");
  const feedbackContainer = document.getElementById("feedback-container");
  const feedbackButtonGood = document.getElementById("feedback-good-btn");
  const feedbackButtonBad = document.getElementById("feedback-bad-btn");
  const inputContainer = document.getElementById("input-container");
  const errorContainer = document.getElementById("error-container");
  const canvas = document.getElementById("visualization-canvas");

  let animationEngine = new AnimationEngine(canvas);

  // document.getElementById("debugScoreDisplay").onclick = function () {
  //   let userAnswers = [
  //     { answer: 95, player: "Player 0", score: 95 },
  //     { answer: 100, player: "Player 1", score: 100 },
  //     { answer: 200, player: "Guillem Tarrach", score: 200 },
  //     { answer: 300, player: "Player 3", score: 300 },
  //   ];
  //   let correctAnswer = [150, 250];
  //   showNewScreen(
  //     function () {
  //       resultContainer.classList.add("future-shown-screen");
  //     },
  //     function () {
  //       foundExcerptElement.textContent = "This is the excerpt";
  //       animationEngine.showVisualization(userAnswers, correctAnswer);
  //     }
  //   );
  // };

  anime({
    targets: "h1 span",
    scale: [0, 1],
    easing: "easeOutElastic(1, .6)",
    // duration: 300,
    delay: function (el, i, l) {
      return i * 100;
    },
  });

  // let gameClient = new OfflineGameClient();
  let gameClient = new OnlineGameClient(
    "ws://" + window.location.hostname + ":8080"
  );

  // Seeding
  document
    .getElementById("shareButton")
    .addEventListener("click", () => gameClient.onShare());
  document.getElementById("playerName").oninput = function () {
    console.log(this);
    gameClient.changePlayerName(this.value);
  };

  // Questions

  let leftover_animations = [];

  function showNewScreen(start_fn, changer_fn, also_change_question = false) {
    leftover_animations.push([start_fn, changer_fn, also_change_question]);
    if (leftover_animations.length > 1) {
      return;
    }
    _showNewScreen(start_fn, changer_fn, also_change_question);
  }
  function _showNewScreen(start_fn, changer_fn, also_change_question) {
    start_fn();

    let question_description_exception = ":not(#question-container)";
    if (also_change_question) {
      questionContainer.classList.add("future-shown-screen");
      question_description_exception = "";
    }
    let animation = anime.timeline({
      duration: 750,
    });
    animation
      .add({
        targets: ".shown-screen" + question_description_exception,
        translateX: [0, window.innerWidth],
        easing: "easeInElastic(1, .6)",
        complete: function (anim) {
          for (let element of [
            ...(also_change_question ? [questionContainer] : []),
            ...[
              loadingContainer,
              inputContainer,
              watingForAnswersContainer,
              resultContainer,
              feedbackContainer,
              errorContainer,
            ],
          ]) {
            if (element.classList.contains("future-shown-screen")) {
              element.classList.remove("future-shown-screen");
              element.classList.add("shown-screen");
            } else {
              element.classList.remove("shown-screen");
            }
          }

          changer_fn();
        },
      })
      .add({
        targets: ".future-shown-screen" + question_description_exception,
        translateX: [-window.innerWidth, 0],
        easing: "easeOutElastic(1, .6)",
        complete: function () {
          leftover_animations.shift();
          if (leftover_animations.length > 0) {
            _showNewScreen(...leftover_animations[0]);
          }
        },
      });
  }

  displayQuestion = function (question) {
    showNewScreen(
      function () {
        inputContainer.classList.add("future-shown-screen");
      },
      function () {
        descriptionElement.textContent = question.description[0];
        dateElement.innerHTML = question.description[1]
          ? `${question.description[1]}`
          : "";
        unitElement.innerHTML = question.description[2]
          ? `${question.description[2]}`
          : "";
        userAnswerElement.value = "";
      },
      true
    );
  };

  displayWaitingForAnswersScreen = function () {
    showNewScreen(
      function () {
        watingForAnswersContainer.classList.add("future-shown-screen");
      },
      function () {}
    );
  };

  displayFeedbackScreen = function () {
    showNewScreen(
      function () {
        feedbackContainer.classList.add("future-shown-screen");
      },
      function () {
        feedbackButtonGood.classList.remove("clicked");
        feedbackButtonBad.classList.remove("clicked");
        feedbackButtonGood.classList.remove("notclicked");
        feedbackButtonBad.classList.remove("notclicked");
      }
    );
  };

  displayError = function (message) {
    showNewScreen(
      function () {
        errorContainer.classList.add("future-shown-screen");
      },
      function () {
        questionContainer.classList.remove("shown-screen");
        if (message)
          document.getElementById("error-message").textContent = message;
      },
      true
    );
  };

  submitBtn.addEventListener("click", () => {
    const userAnswer = parseNumberString(userAnswerElement.value);
    if (userAnswer === null) {
      userAnswerElement.classList.add("error");
      return;
    } else {
      userAnswerElement.classList.remove("error");
    }
    gameClient.submitAnswer(userAnswer);
  });
  nextQuestionBtn.addEventListener("click", () =>
    gameClient.handleNextQuestion()
  );

  feedbackButtonGood.onclick = function () {
    if (
      this.classList.contains("clicked") ||
      this.classList.contains("notclicked")
    )
      return;

    feedbackButtonGood.classList.add("clicked");
    feedbackButtonBad.classList.add("notclicked");
    gameClient.voteQuestion("good");
  };
  feedbackButtonBad.onclick = function () {
    if (
      this.classList.contains("clicked") ||
      this.classList.contains("notclicked")
    )
      return;

    feedbackButtonGood.classList.add("notclicked");
    feedbackButtonBad.classList.add("clicked");
    gameClient.voteQuestion("bad");
  };
  gameClient.onQuestionChecking = function (
    userAnswers,
    correctAnswer,
    excerpt
  ) {
    showNewScreen(
      function () {
        resultContainer.classList.add("future-shown-screen");
      },
      function () {
        foundExcerptElement.textContent = excerpt;
        animationEngine.showVisualization(userAnswers, correctAnswer);
      }
    );
  };
});

// ==============================================================================================
//  Seeds and sharing
// ==============================================================================================

function mulberry32(seed) {
  return function () {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function getSeedFromURL() {
  // Get the current URL
  let currentUrl = new URL(window.location.href);

  let seed = null;

  // Check if the search parameter already exists
  if (currentUrl.searchParams.has("s")) {
    // Get seed and remove the existing search parameter
    seed = currentUrl.searchParams.get("s");
    currentUrl.searchParams.delete("s");
  } else {
    seed = generateSeed();
  }

  // Get the modified URL as a string
  const modifiedUrl = currentUrl.toString();

  // Change the current URL without refreshing the page
  history.pushState(null, "", modifiedUrl);

  return seed;
}

function generateSeed(rng = Math.random) {
  const consonants = "bcdfghjklmnpqrstvwxyz".toUpperCase();
  const vowels = "aeiou".toUpperCase();
  let seed = "";
  for (let i = 0; i < 12; i++) {
    if (i % 2 === 0) {
      seed += consonants.charAt(Math.floor(rng() * consonants.length));
    } else {
      seed += vowels.charAt(Math.floor(rng() * vowels.length));
    }
  }
  return seed;
}

function decodeSeed(seed) {
  const consonants = "bcdfghjklmnpqrstvwxyz".toUpperCase();
  const vowels = "aeiou".toUpperCase();
  let decodedSeed = 0;
  for (let i = 0; i < seed.length; i++) {
    if (i % 2 === 0) {
      decodedSeed =
        decodedSeed * consonants.length + consonants.indexOf(seed.charAt(i));
    } else {
      decodedSeed =
        decodedSeed * vowels.length + vowels.indexOf(seed.charAt(i));
    }
  }
  return decodedSeed;
}

function encodeSeed(decodedSeed) {
  const consonants = "bcdfghjklmnpqrstvwxyz".toUpperCase();
  const vowels = "aeiou".toUpperCase();
  let seed = "";
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

// ==============================================================================================
// Parsing numbers
// ==============================================================================================

function parseNumberString(input) {
  // Define multipliers
  const multipliers = {
    hundred: 100,
    thousand: 1000,
    million: 1e6,
    billion: 1e9,
    trillion: 1e12,
    quadrillion: 1e15,
    quintillion: 1e18,
    sextillion: 1e21,
    septillion: 1e24,
    octillion: 1e27,
    nonillion: 1e30,
    decillion: 1e33,
    undecillion: 1e36,
    duodecillion: 1e39,
    tredecillion: 1e42,
    quattuordecillion: 1e45,
    quindecillion: 1e48,
    sexdecillion: 1e51,
    septendecillion: 1e54,
    octodecillion: 1e57,
    novemdecillion: 1e60,
    vigintillion: 63,
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

// ==============================================================================================
//  Cookies
// ==============================================================================================

function setCookie(name, value, days) {
  var expires = "";
  if (days) {
    var date = new Date();
    date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
    expires = "; expires=" + date.toUTCString();
  }
  document.cookie = name + "=" + (value || "") + expires + "; path=/";
}
function getCookie(name) {
  var nameEQ = name + "=";
  var ca = document.cookie.split(";");
  for (var i = 0; i < ca.length; i++) {
    var c = ca[i];
    while (c.charAt(0) == " ") c = c.substring(1, c.length);
    if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length, c.length);
  }
  return null;
}
function eraseCookie(name) {
  document.cookie = name + "=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;";
}

// ==============================================================================================
// Abstractions and implementations for online/offline
// ==============================================================================================

class GameClient {
  constructor() {
    this.onQuestionChecking = function (userAnswer, correctAnswer, excerpt) {};
  }

  startNewGame() {
    throw new Error("startNewGame method not implemented.");
  }

  joinExistingGame() {
    throw new Error("joinExistingGame method not implemented.");
  }

  startRound() {
    throw new Error("startRound method not implemented.");
  }

  submitAnswer(userAnswer) {
    throw new Error("submitAnswer method not implemented.");
  }

  voteQuestion() {
    throw new Error("voteQuestion method not implemented.");
  }

  changePlayerName(name) {
    throw new Error("changePlayerName method not implemented.");
  }

  on() {
    throw new Error("on method not implemented.");
  }
}

// Online mode

class OnlineGameClient extends GameClient {
  constructor(serverUrl) {
    super();

    this.serverUrl = serverUrl;
    this.socket = null;
    this.roomCode = null;

    let uuid_cookie = getCookie("guesstimate-uuid");
    if (!uuid_cookie) {
      uuid_cookie = this.generateUUID();
      setCookie("guesstimate-uuid", uuid_cookie, 365);
    }
    this.uuid = uuid_cookie;

    let player_name = getCookie("guesstimate-player-name");
    let player_name_url_part = "";
    if (player_name) {
      document.getElementById("playerName").value = player_name;
      player_name_url_part = `&playerName=${encodeURIComponent(player_name)}`;
    }

    this.onMessage = this.onMessage.bind(this);

    // Start connection
    this.socket = new WebSocket(
      this.serverUrl + "?uuid=" + this.uuid + player_name_url_part
    );
    this.socket.onmessage = this.onMessage;
    this.socket.onopen = () => {
      console.log("Connected to the server.");

      let currentUrl = new URL(window.location.href);
      if (currentUrl.searchParams.has("r")) {
        this.joinExistingGame(currentUrl.searchParams.get("r"));
      } else {
        this.startNewGame();
      }
    };
    this.socket.onclose = () => {
      console.log("Disconnected from the server.");
      displayError("Could not connect to the server.");
    };
    this.socket.onerror = (error) => {
      console.error("WebSocket error:", error);
      displayError("Could not connect to the server.");
    };
  }

  onMessage(event) {
    const data = JSON.parse(event.data);
    console.log("Message from server:", data);

    switch (data.action) {
      case "player_name":
        document.getElementById("playerName").value = data.name;
        break;
      case "room_created":
        this.roomCode = data.roomCode;
        console.log(`Room created with code: ${this.roomCode}`);
        this.startRound();
        break;
      case "room_joined":
        this.roomCode = data.roomCode;
        document.getElementById("playerName").style.display = "inline-block";
        break;
      case "player_joined":
        console.log(data.message);
        break;
      case "new_question":
        // this.removeRoomCodeFromURL();
        const question = data.question;
        displayQuestion(question);
        break;
      case "answer_submitted":
        displayWaitingForAnswersScreen();
        break;
      case "round_scores":
        this.onQuestionChecking(data.data, data.correct_answer, data.excerpt);
        break;
      case "waiting_for_everyone_to_be_ready":
        displayFeedbackScreen();
        break;
      case "error":
        console.error("Server error:", data.code);
        switch (data.code) {
          case "room_not_found":
            this.removeRoomCodeFromURL();
            displayError("Room not found.");
            break;
          default:
            break;
        }
        break;
    }
  }

  send(action, payload = {}) {
    if (this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ action, ...payload }));
    } else {
      console.error("Socket is not open. Cannot send message.");
    }
  }

  putRoomCodeInURL() {
    let currentUrl = new URL(window.location.href);
    currentUrl.searchParams.set("r", this.roomCode);
    const modifiedUrl = currentUrl.toString();

    // Change the current URL without refreshing the page
    history.pushState(null, "", modifiedUrl);
  }

  removeRoomCodeFromURL() {
    let currentUrl = new URL(window.location.href);
    currentUrl.searchParams.delete("r");
    const modifiedUrl = currentUrl.toString();

    // Change the current URL without refreshing the page
    history.pushState(null, "", modifiedUrl);
  }

  // Room management
  startNewGame() {
    this.send("create_room");
  }

  joinExistingGame(roomCode) {
    this.send("join_room", { roomCode });
    this.roomCode = roomCode;
  }

  // Game actions
  startRound() {
    this.send("start_round");
  }

  submitAnswer(answer) {
    this.send("submit_answer", { answer });
  }

  voteQuestion(vote) {
    this.send("vote_question", { vote }); // 'good' or 'bad'
  }

  changePlayerName(name) {
    this.send("player_name", { name });
    setCookie("guesstimate-player-name", name, 365);
  }

  // Other
  generateUUID() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
      /[xy]/g,
      function (c) {
        var r = (Math.random() * 16) | 0,
          v = c == "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
      }
    );
  }

  //

  onShare() {
    let sharable_code = this.roomCode;
    if (!sharable_code) {
      return;
    }

    // Get the current URL
    let currentUrl = new URL(window.location.href);

    // Check if the search parameter already exists
    if (currentUrl.searchParams.has("r")) {
      // Update the existing search parameter
      currentUrl.searchParams.set("r", sharable_code);
    } else {
      // Add the search parameter
      currentUrl.searchParams.append("r", sharable_code);
    }

    // Get the modified URL as a string
    const modifiedUrl = currentUrl.toString();

    console.log("Modified URL:", modifiedUrl);

    const tooltip = document.getElementById("copy-tooltip");
    const button = document.getElementById("shareButton");

    // Copy the modified URL to the clipboard
    navigator.clipboard
      .writeText(modifiedUrl)
      .then(function () {
        console.log("URL copied to clipboard");

        tooltip.textContent = "Copied!";
      })
      .catch(function (err) {
        alert("Failed to copy " + modifiedUrl + " : ", err);
        tooltip.textContent = "Failed to copy. Pasted to bar.";
        window.location.href = url;
      });

    tooltip.style.visibility = "visible";

    const rect = button.getBoundingClientRect();
    tooltip.style.bottom = rect.bottom - rect.top + 5 + "px";
    tooltip.style.right = "5px";
    setTimeout(() => {
      tooltip.style.visibility = "hidden";
    }, 2000);

    // this.putRoomCodeInURL();

    document.getElementById("playerName").style.display = "inline-block";
  }

  handleNextQuestion() {
    this.send("ready_for_next_round");
  }
}

// Offline mode

class OfflineGameClient extends GameClient {
  constructor() {
    super();

    this.allQuestions = [];
    this.lastQuestionsIndices = [];
    this.currentQuestionIndex = 0;
    this.seed = null;

    fetch("data.json.gz", {
      headers: {
        "Content-Encoding": "gzip",
      },
    })
      .then((response) => response.arrayBuffer())
      .then((buffer) => {
        // Decompress the data using pako
        const decompressedData = pako.inflate(new Uint8Array(buffer), {
          to: "string",
        });
        const jsonData = JSON.parse(decompressedData);
        this.allQuestions = jsonData;
        this.startRound();
      })
      .catch((error) => {
        console.error("Error fetching or decompressing data:", error);
      });
  }

  startNewGame() {
    console.log("Offline game started.");
  }

  joinExistingGame() {
    console.log("Offline game joined.");
  }

  startRound() {
    if (this.allQuestions.length === 0) {
      return null;
    }
    if (!this.seed) this.seed = getSeedFromURL() || generateSeed();
    else {
      this.seed = generateSeed(mulberry32(decodeSeed(this.seed)));
    }

    const rng = mulberry32(decodeSeed(this.seed));

    this.currentQuestionIndex = null;
    while (this.currentQuestionIndex === null) {
      const randomIndex = Math.floor(rng() * this.allQuestions.length);
      if (!this.lastQuestionsIndices.includes(randomIndex)) {
        this.currentQuestionIndex = randomIndex;
        this.lastQuestionsIndices.push(randomIndex);
        if (this.lastQuestionsIndices.length > 10) {
          this.lastQuestionsIndices.shift();
        }
      }
    }

    const question = this.allQuestions[this.currentQuestionIndex];
    displayQuestion(question);
  }

  submitAnswer(userAnswer) {
    const question = this.allQuestions[this.currentQuestionIndex];
    const correctAnswer = question.answer;
    this.onQuestionChecking(
      { answer: userAnswer },
      correctAnswer,
      question.excerpt
    );
  }

  voteQuestion() {
    console.log("Offline question voted.");
  }

  on(action, callback) {
    this.eventHandlers[action] = callback;
  }

  onShare() {
    let sharable_code = this.seed;
    if (!sharable_code) {
      return;
    }

    // Get the current URL
    let currentUrl = new URL(window.location.href);

    // Check if the search parameter already exists
    if (currentUrl.searchParams.has("s")) {
      // Update the existing search parameter
      currentUrl.searchParams.set("s", sharable_code);
    } else {
      // Add the search parameter
      currentUrl.searchParams.append("s", sharable_code);
    }

    // Get the modified URL as a string
    const modifiedUrl = currentUrl.toString();

    // // Change the current URL without refreshing the page
    // history.pushState(null, '', modifiedUrl);

    // Copy the modified URL to the clipboard
    navigator.clipboard
      .writeText(modifiedUrl)
      .then(function () {
        console.log("URL copied to clipboard");
      })
      .catch(function (err) {
        alert("Failed to copy " + modifiedUrl + " : ", err);
      });
  }

  handleNextQuestion() {
    this.startRound();
  }
}

// Score animations

function toFixed_leq(x, n) {
  let s = x.toFixed(n);
  // Remove trailing zeros
  s = s.replace(/(\.\d*?[1-9])0+|\.0*$/, "$1");
  return s;
}

function calculateRoundLogTicks(maxValue, numTicks, minDistance = 0) {
  const logBase = 10;

  let maxLog = 0;
  while (customScale(Math.pow(logBase, maxLog)) < maxValue) {
    maxLog++;
  }
  maxLog--;

  let allowedLeadingDigits = [];
  if (maxLog <= 4) {
    allowedLeadingDigits = [1, 2, 3, 4, 5, 6, 7, 8, 9];
  } else if (maxLog <= 8) {
    allowedLeadingDigits = [1, 2, 5];
  } else if (maxLog <= 12) {
    allowedLeadingDigits = [1, 3];
  } else {
    allowedLeadingDigits = [1];
  }

  let currentLog = maxLog;
  let currentLeadingDigitIndex = allowedLeadingDigits.length - 1;

  let ticks = [];
  let i = 0;
  while (i < numTicks) {
    const tickValue =
      allowedLeadingDigits[currentLeadingDigitIndex] *
      Math.pow(logBase, currentLog);
    const scaledValue = customScale(tickValue);
    if (scaledValue <= maxValue) {
      if (
        ticks.length == 0 ||
        (customScale(ticks[ticks.length - 1]) - scaledValue > minDistance &&
          scaledValue - customScale(0) > minDistance)
      )
        ticks.push(tickValue);
      i++;
    }

    currentLeadingDigitIndex--;
    if (currentLeadingDigitIndex < 0) {
      currentLeadingDigitIndex = allowedLeadingDigits.length - 1;
      currentLog--;
    }
  }
  ticks.push(0);
  return ticks.reverse();
}

function customScale(x, k = 1000.0) {
  let sign = x < 0 ? -1 : 1;
  x = Math.abs(x);
  return sign * (Math.log(k + x) - Math.log(k));
}

class AnimationEngine {
  constructor(canvas) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d");
  }

  displayNumber(number, options = { exact: true, longForm: true }) {
    const SHORT_SYMBOL = ["", "k", "M", "B", "T", "Q", "Qn"];
    const LONG_SYMBOL = [
      "",
      "thousand",
      "million",
      "billion",
      "trillion",
      "quadrillion",
      "quintillion",
    ];

    function abbreviateNumber(number, longForm, exact) {
      let tier = (Math.log10(Math.abs(number)) / 3) | 0;

      if (tier === 0) return number.toLocaleString();

      let first_line = "";
      if (tier < SHORT_SYMBOL.length) {
        const suffix = longForm ? LONG_SYMBOL[tier] : SHORT_SYMBOL[tier];
        const scale = Math.pow(10, tier * 3);

        const scaled = number / scale;

        if (!exact) {
          const scaled_string = toFixed_leq(scaled, 1);
          first_line = scaled_string + " " + suffix + "\n";
        } else {
          // Should we return the number as is?
          if (number >= 1e10) first_line = scaled + " " + suffix + "\n";
        }
      }

      let second_line = "";
      if (exact && number < 1e10) second_line = number.toLocaleString();
      else {
        let exponent = Math.floor(Math.log10(Math.abs(number)));
        let mantissa = number * Math.pow(10, -exponent);
        mantissa = Math.round(mantissa * 1000000000) / 1000000000;
        if (!exact) mantissa = toFixed_leq(mantissa, 1);
        if (mantissa == 1) second_line = `10^${exponent}`;
        else if (mantissa == -1) second_line = `-10^${exponent}`;
        else second_line = `${mantissa} x 10^${exponent}`;
      }

      return first_line + second_line;
    }

    if (number === 0) {
      return "0";
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

  showVisualization(userAnswerData, correctAnswer) {
    const self = this;

    const ideal_width = document.body.clientWidth > 800 ? 800 : 400;
    const ideal_height = 200;
    const ideal_margin = 10;
    const ideal_x_offset = 50;
    const axisY = 150;

    let width = ideal_width;
    let height = ideal_height;
    let margin = ideal_margin;
    let padding = 10;
    let global_scale = 1.0;
    let x_offset = ideal_x_offset;
    let effective_width = width - 2 * x_offset;

    const canvas = this.canvas;
    const context = this.context;

    function resizeCanvas() {
      const bodyStyle = window.getComputedStyle(document.body);
      width = Math.min(document.body.clientWidth, ideal_width);
      global_scale = width / ideal_width;
      height = ideal_height * global_scale;
      margin = ideal_margin * global_scale;
      x_offset = ideal_x_offset * global_scale;
      effective_width = width - 2 * x_offset;

      const dpi = window.devicePixelRatio;
      canvas.width = width * dpi;
      canvas.height = height * dpi;
      context.scale(dpi, dpi);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
    }

    resizeCanvas();

    const correctAnswerIsInterval = typeof correctAnswer == "object";
    const userAnswers = [];
    for (let i = 0; i < userAnswerData.length; i++) {
      userAnswers.push(userAnswerData[i].answer);
    }
    const answers = userAnswers.concat(
      correctAnswerIsInterval ? [...correctAnswer] : [correctAnswer]
    );
    const colors = Array(userAnswers.length)
      .fill("#BB0000")
      .concat(correctAnswerIsInterval ? ["green", "green"] : ["green"]);
    let answersX = [];
    for (let i = 0; i < answers.length; i++) {
      answersX[i] = customScale(answers[i]);
    }
    const _minAnswerX = Math.min(...answersX);
    const _maxAnswerX = Math.max(...answersX);

    let _origMaxX, _origMinX;
    if (_minAnswerX > 0) {
      _origMaxX = _minAnswerX + _maxAnswerX;
      _origMinX = 0.0;
    } else if (_maxAnswerX < 0) {
      _origMinX = _maxAnswerX + _minAnswerX;
      _origMaxX = 0.0;
    } else {
      _origMinX = _minAnswerX;
      _origMaxX = _maxAnswerX;
    }

    // Animate zoom
    const duration = 3000;
    const point_sum_duration = 1000;
    const startTime = performance.now();

    function transition(x) {
      return Math.sin((x * Math.PI) / 2);
    }

    let animation_done = false;
    function animate() {
      const currentTime = performance.now();
      const elapsedTime = currentTime - startTime;
      const t = transition(Math.min(elapsedTime / duration, 1));
      const t_extended = Math.max(
        Math.min(
          ((elapsedTime / duration - 1) * duration) / point_sum_duration,
          1
        ),
        0
      );

      const initialZoom = 10.0;
      let origMaxX =
        _origMaxX > 0
          ? customScale(initialZoom) +
            t * (_origMaxX - customScale(initialZoom))
          : 0.0;
      let origMinX =
        _origMinX < 0
          ? -customScale(initialZoom) +
            t * (_origMinX + customScale(initialZoom))
          : 0.0;

      // Draw X-axis ticks
      const numTicks = 40;
      const tickScale =
        0.04 * Math.max(Math.abs(_origMaxX), Math.abs(_origMinX));
      let tickValues = calculateRoundLogTicks(
        origMaxX - origMinX,
        numTicks,
        tickScale
      );
      if (origMinX < 0) {
        // Copy the positive ticks as negative ticks
        tickValues = tickValues
          .map((x) => -x)
          .reverse()
          .slice(0, -1)
          .concat(tickValues);
      }

      const fontSize = 10 * global_scale;

      context.clearRect(0, 0, width, height);
      context.save();

      // Redraw line
      context.beginPath();
      context.moveTo(0, axisY);
      context.lineTo(width, axisY);
      context.strokeStyle = "black";
      context.lineWidth = 2;
      context.stroke();

      // Redraw X-axis ticks
      let lastX = -Infinity;
      for (let i = 0; i < tickValues.length; i++) {
        const tickValue = tickValues[i];
        const x =
          (effective_width * (customScale(tickValue) - origMinX)) /
          (origMaxX - origMinX);

        // Draw tick line
        context.beginPath();
        context.moveTo(x_offset + x, axisY - margin);
        context.lineTo(x_offset + x, axisY + margin);
        context.strokeStyle = "black";
        context.lineWidth = 1;
        context.stroke();

        context.font = fontSize.toFixed(1) + "px Arial";
        context.fillStyle = "black";
        context.textAlign = "center";

        // Draw tick label
        const labelText = self.displayNumber(tickValue, {
          exact: false,
          longForm: false,
        });
        const lines = labelText.split("\n");

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
            context.fillText(
              lines[j],
              x_offset + x,
              axisY + 2 * margin + j * lineHeight
            );
          }
          lastX = x + tickLabelWidth / 2;
        }
      }

      for (let i = 0; i < answers.length; i++) {
        // Redraw circle of answer
        let x =
          (effective_width * (answersX[i] - origMinX)) / (origMaxX - origMinX);
        context.beginPath();
        context.arc(x_offset + x, axisY, 5, 0, 2 * Math.PI);
        context.fillStyle = colors[i];
        context.fill();

        // Redraw value text of answer
        context.font = fontSize.toFixed(1) + "px Manrope";
        context.fillStyle = colors[i];
        context.textAlign = "center";

        let labelText = self.displayNumber(answers[i]);
        if (i < userAnswers.length) {
          let effective_t = Math.min(1, t_extended * 1.2); // TO=o make sure you actually see the correct score in the end
          let totalScore = Math.round(
            userAnswerData[i].totalScore -
              userAnswerData[i].score +
              effective_t * userAnswerData[i].score
          );
          if (userAnswerData[i].player) {
            labelText =
              labelText +
              "\n\n" +
              ("(+" + userAnswerData[i].score + ")") +
              "\n" +
              totalScore +
              " pts" +
              "\n" +
              userAnswerData[i].player;
          }
        }
        const lines = labelText.split("\n");
        const lineHeight = -fontSize;
        const totalHeight = lines.length * lineHeight;

        // Draw box around text
        let textWidth = 0;
        for (let j = 0; j < lines.length; j++) {
          let w = context.measureText(lines[j]).width;
          textWidth = Math.max(textWidth, w);
        }
        let textHeight = -lines.length * lineHeight;
        let textX = x_offset + x;
        let textY = axisY - 2 * margin - textHeight;
        context.fillStyle = "white";
        context.strokeStyle = colors[i];
        context.lineWidth = 2;
        // Draw comic dialog box
        const pointerWidth = margin;
        const pointerX = textX;
        const pointerY = axisY;

        context.beginPath();
        context.moveTo(textX - textWidth / 2 - padding, textY - padding);
        context.lineTo(textX + textWidth / 2 + padding, textY - padding);
        context.lineTo(
          textX + textWidth / 2 + padding,
          textY + textHeight + padding
        );
        context.lineTo(
          pointerX + pointerWidth / 2,
          textY + textHeight + padding
        );
        context.lineTo(pointerX, pointerY);
        context.lineTo(
          pointerX - pointerWidth / 2,
          textY + textHeight + padding
        );
        context.lineTo(
          textX - textWidth / 2 - padding,
          textY + textHeight + padding
        );
        context.closePath();
        context.fill();
        context.stroke();
        context.lineWidth = 1;
        context.fillStyle = colors[i];

        // Draw text
        for (let j = lines.length - 1; j >= 0; j--) {
          context.fillText(
            lines[j],
            x_offset + x,
            axisY - 2 * margin + j * lineHeight
          );
        }
      }

      if (correctAnswerIsInterval) {
        // Draw green line
        context.beginPath();
        context.moveTo(
          x_offset +
            (effective_width * (answersX[answersX.length - 2] - origMinX)) /
              (origMaxX - origMinX),
          axisY
        );
        context.lineTo(
          x_offset +
            (effective_width * (answersX[answersX.length - 1] - origMinX)) /
              (origMaxX - origMinX),
          axisY
        );
        context.strokeStyle = colors[answersX.length - 1];
        context.lineWidth = 6;
        context.stroke();
      }

      context.restore();

      if (t_extended < 1) {
        requestAnimationFrame(animate);
      } else {
        animation_done = true;
      }
    }

    canvas.onmousemove = function (event) {
      // Reorder the play scores so that the hovered one is on top (of the player ones), then redraw

      let x = event.offsetX;
      let y = event.offsetY;
      let found = false;

      for (let i = 0; i < userAnswerData.length; i++) {
        let x_answer =
          (effective_width * (answersX[i] - _origMinX)) /
          (_origMaxX - _origMinX);
        if (
          x > x_offset + x_answer - 4 &&
          x < x_offset + x_answer + 4 &&
          y > axisY - 10 &&
          y < axisY + 8
        ) {
          let new_index = userAnswerData.length - 1;

          let tmp = answers[new_index];
          answers[new_index] = answers[i];
          answers[i] = tmp;

          tmp = userAnswerData[new_index];
          userAnswerData[new_index] = userAnswerData[i];
          userAnswerData[i] = tmp;

          tmp = answersX[new_index];
          answersX[new_index] = answersX[i];
          answersX[i] = tmp;

          found = true;
          break;
        }
      }

      window.addEventListener("resize", function () {
        resizeCanvas();
        if (animation_done) animate();
      });

      if (found) animate();
    };

    requestAnimationFrame(animate);
  }
}
