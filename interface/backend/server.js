import { query } from "express";
import fs from "fs";
import http from "http";
import { WebSocketServer } from "ws";
import url from "url";

class Room {
  constructor() {
    this.roomCode = generateRoomCode();
    this.players = new Map(); // uuid -> ws
    this.currentQuestion = null;
    this.totalScores = new Map(); // uuid -> score
    this.answersThisRound = new Map(); // uuid -> answer
    this.readyForNextRound = new Map(); // uuid -> answer
    this.state = null; // "waiting_for_answers", "waiting_for_next_round"
  }

  startRound() {
    const questionIndex = getRandomQuestionIndex();
    const question = ALL_QUESTIONS[questionIndex];
    this.currentQuestion = { question, index: questionIndex };
    this.answersThisRound = new Map();

    broadcast(this.roomCode, {
      action: "new_question",
      question: this.currentQuestion.question,
    });

    this.state = "waiting_for_answers";
  }

  proceedIfAllAnswersAreSubmitted() {
    if (this.answersThisRound.size !== this.players.size) return false;

    const question = this.currentQuestion.question;
    const player_answers = this.answersThisRound;
    const player_scores = computeScores(player_answers, question);
    const player_answers_and_scores = Array.from(player_answers).map(
      ([player_uuid, answer]) => ({
        player: this.players.get(player_uuid).playerName,
        answer,
        score: player_scores.get(player_uuid),
      })
    );
    // Add scores
    this.players.forEach((player, uuid) => {
      const score = player_scores.get(uuid) || 0;
      this.totalScores.set(uuid, (this.totalScores.get(uuid) || 0) + score);
    });

    broadcast(this.roomCode, {
      action: "round_scores",
      data: player_answers_and_scores,
      correct_answer: question.answer,
      excerpt: question.excerpt,
    });
    this.currentQuestion = null;

    this.readyForNextRound = new Map();
    this.state = "waiting_for_next_round";
    return true;
  }

  proceedIfEveryoneIsReadyForNextRound() {
    if (this.readyForNextRound.size === this.players.size) {
      this.startRound();
      return true;
    }
    return false;
  }

  proceedAccordingToState() {
    if (this.state === "waiting_for_answers") {
      this.proceedIfAllAnswersAreSubmitted();
    } else if (this.state === "waiting_for_next_round") {
      this.proceedIfEveryoneIsReadyForNextRound();
    }
  }
}

// Load ALL_QUESTIONS from a JSON file at start-up
const ALL_QUESTIONS = JSON.parse(fs.readFileSync("data.json", "utf8"));
const GLOBAL_VOTES = ALL_QUESTIONS.map(() => ({ good: 1, bad: 1 }));

// Map to store room data
const rooms = new Map();

// Create HTTP server
const server = http.createServer();

// Create WebSocket server
const wss = new WebSocketServer({ server });

wss.on("connection", (ws, req) => {
  const requestQuery = url.parse(req.url, true).query;
  if (!requestQuery || !requestQuery.uuid) {
    return;
  }
  ws.playerName = generatePlayerName();
  ws.uuid = requestQuery.uuid;
  ws.on("message", (message) => {
    try {
      const data = JSON.parse(message);

      switch (data.action) {
        case "create_room": {
          const room = new Room();
          const roomCode = room.roomCode;
          rooms.set(roomCode, room);
          room.players.set(ws.uuid, ws);
          ws.roomCode = roomCode;
          ws.send(JSON.stringify({ action: "room_created", roomCode }));
          break;
        }

        case "join_room": {
          const { roomCode } = data;
          const room = rooms.get(roomCode);
          if (room) {
            room.players.set(ws.uuid, ws);
            ws.roomCode = roomCode;
            room.totalScores.set(ws.uuid, 0);
            broadcast(roomCode, {
              action: "player_joined",
              message: "A new player has joined the room.",
            });

            if (room.state == "waiting_for_answers") {
              ws.send(
                JSON.stringify({
                  action: "new_question",
                  question: room.currentQuestion.question,
                })
              );
            } else if (room.state == "waiting_for_next_round") {
              room.readyForNextRound.set(ws.uuid, true);
            }
          } else {
            ws.send(
              JSON.stringify({ action: "error", code: "room_not_found" })
            );
          }
          break;
        }

        case "start_round": {
          const roomCode = ws.roomCode;
          const room = rooms.get(roomCode);
          if (!room) return;

          room.startRound();
          break;
        }

        case "submit_answer": {
          const { answer } = data;
          const roomCode = ws.roomCode;
          const room = rooms.get(roomCode);
          if (!room || !room.currentQuestion) return;

          room.answersThisRound.set(ws.uuid, answer);

          if (!room.proceedIfAllAnswersAreSubmitted()) {
            ws.send(JSON.stringify({ action: "answer_submitted" }));
          }
          break;
        }

        case "ready_for_next_round": {
          const roomCode = ws.roomCode;
          const room = rooms.get(roomCode);
          if (!room) return;

          room.readyForNextRound.set(ws.uuid, true);

          room.proceedIfEveryoneIsReadyForNextRound();
          break;
        }

        case "vote_question": {
          const { vote } = data; // "good" or "bad"
          if (vote !== "good" && vote !== "bad") return;
          const roomCode = ws.roomCode;
          const room = rooms.get(roomCode);
          if (!room || !room.currentQuestion) return;

          const questionIndex = room.currentQuestion.index;
          if (vote === "good") GLOBAL_VOTES[questionIndex].good++;
          if (vote === "bad") GLOBAL_VOTES[questionIndex].bad++;

          break;
        }

        default:
          ws.send(JSON.stringify({ action: "error", code: "unknown_action" }));
      }
    } catch (err) {
      console.log(err);
      ws.send(
        JSON.stringify({ action: "error", code: "invalid_message_format" })
      );
    }
  });

  ws.on("close", () => {
    const roomCode = ws.roomCode;
    if (roomCode && rooms.has(roomCode)) {
      const room = rooms.get(roomCode);
      room.players.delete(ws.uuid);
      room.answersThisRound.delete(ws.uuid);
      room.readyForNextRound.delete(ws.uuid);

      if (room.players.length === 0) {
        rooms.delete(roomCode);
      } else {
        broadcast(roomCode, {
          action: "player_left",
          message: "A player has left the room.",
        });
        room.proceedAccordingToState();
      }
    }
  });
});

function generateRoomCode() {
  return Math.random().toString(36).substr(2, 5).toUpperCase();
}

function generatePlayerName() {
  return "Player" + Math.floor(Math.random() * 1000);
}

function broadcast(roomCode, message) {
  const room = rooms.get(roomCode);
  if (room) {
    room.players.forEach((player) => {
      player.send(JSON.stringify(message));
    });
  }
}

// ============================================================================
//  Scores
// ============================================================================

/*
Principles:
1. First map everything into quantities that can take any real values:
  - unbounded -> unchanged
  - bounded on one side -> do log from the bound
  - bounded on both sides -> do logit transformation
2. Normalize so that the average standard deviation across all questions
3. Normalize Bayesian-ly according to the question
*/

let SCORE_GLOBAL_NORMALIZATION_CONSTANTS = {
  "[]": 1.0,
  "[)": 1.0,
  "(]": 1.0,
  "()": 1.0,
};

function update_score_global_normalization_constants() {
  const alpha = 1;
  const beta = 1.0;

  let sum_of_squares = {
    "[]": 0.0,
    "[)": 0.0,
    "(]": 0.0,
    "()": 0.0,
  };
  let num_samples = {
    "[]": 0,
    "[)": 0,
    "(]": 0,
    "()": 0,
  };
  for (let question of ALL_QUESTIONS) {
    const L = question["scale-interval"]["lower_bound"];
    const U = question["scale-interval"]["upper_bound"];

    const answer_transformed = transform_according_to_LU(
      question.answer,
      L,
      U,
      false
    );
    const bound_type =
      L === null ? (U === null ? "()" : "(]") : U === null ? "[)" : "[]";
    if (!isNaN(answer_transformed)) {
      sum_of_squares[bound_type] += answer_transformed * answer_transformed;
      num_samples[bound_type]++;
    }
  }

  for (let bound_type in SCORE_GLOBAL_NORMALIZATION_CONSTANTS) {
    SCORE_GLOBAL_NORMALIZATION_CONSTANTS[bound_type] = Math.sqrt(
      (sum_of_squares[bound_type] + alpha * beta * beta) /
        (num_samples[bound_type] + alpha)
    );
  }
  console.log("Normalization constants:", SCORE_GLOBAL_NORMALIZATION_CONSTANTS);
}
update_score_global_normalization_constants();

function scale_independet_difference(a, b) {
  return (50.0 * (a - b)) / (40.0 + Math.abs(a));
}

function logit(x) {
  return Math.log(x / (1 - x));
}

function transform_according_to_LU(x, L, U, normalize = true) {
  if (L !== null) {
    if (U === null) {
      return (
        Math.log(x - L) /
        (normalize ? SCORE_GLOBAL_NORMALIZATION_CONSTANTS["[)"] : 1.0)
      );
    } else {
      const x_normalized = (x - L) / (U - L);
      return (
        logit(x_normalized) /
        (normalize ? SCORE_GLOBAL_NORMALIZATION_CONSTANTS["[]"] : 1.0)
      );
    }
  } else {
    if (U === null) {
      return x / (normalize ? SCORE_GLOBAL_NORMALIZATION_CONSTANTS["()"] : 1.0);
    } else {
      return (
        Math.log(U - x) /
        (normalize ? SCORE_GLOBAL_NORMALIZATION_CONSTANTS["(]"] : 1.0)
      );
    }
  }
}

function compute_std_bayesian_posterior(samples) {
  const prior_estimate = 1.0;
  const prior_strength = 2;

  let sum_of_squares = 0;
  let num_samples = 0;
  for (let sample of samples) {
    if (!isNaN(sample)) {
      sum_of_squares += sample * sample;
      num_samples += 1;
    }
  }

  return Math.sqrt(
    (sum_of_squares + prior_strength * prior_estimate * prior_estimate) /
      (num_samples + prior_strength)
  );
}

function normalCDF(x) {
  // Abramowitz and Stegun approximation for normal CDF
  const a1 = 0.254829592,
    a2 = -0.284496736,
    a3 = 1.421413741;
  const a4 = -1.453152027,
    a5 = 1.061405429;
  const p = 0.3275911;

  const sign = x < 0 ? -1 : 1;
  x = Math.abs(x) / Math.SQRT2;

  const t = 1 / (1 + p * x);
  const erf =
    1 - ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);

  return 0.5 * (1 + sign * erf);
}

function normalSurvivalProbability(x) {
  return Math.max(0.0, Math.min(1.0, 2 * (1 - normalCDF(Math.abs(x)))));
}

function computeScores(player_answers, question) {
  const L = question["scale-interval"]["lower_bound"];
  const U = question["scale-interval"]["upper_bound"];
  const correct = question.answer;

  console.log("-------");

  let correct_transformed = transform_according_to_LU(correct, L, U);
  let answers_transformed = new Map();
  for (let [player, answer] of player_answers.entries()) {
    answers_transformed.set(player, transform_according_to_LU(answer, L, U));
  }
  console.log(correct_transformed, answers_transformed);

  const normalization_constant = compute_std_bayesian_posterior([
    correct_transformed,
    ...answers_transformed.values(),
  ]);

  let answers_normalized = new Map();
  for (let [player, transformed] of answers_transformed.entries()) {
    answers_normalized.set(
      player,
      (transformed - correct_transformed) / normalization_constant
    );
  }
  console.log(normalization_constant, answers_normalized);

  let scores = new Map();
  for (let [player, normalized] of answers_normalized.entries()) {
    scores.set(
      player,
      Math.round(1000 * normalSurvivalProbability(4.0 * normalized))
    );
  }
  return scores;
}

function getRandomQuestionIndex() {
  const question_probablilities_unnormalized = GLOBAL_VOTES.map(
    ({ good, bad }) => good / (good + bad)
  );
  const sum = question_probablilities_unnormalized.reduce((a, b) => a + b, 0);
  const question_probablilities = question_probablilities_unnormalized.map(
    (p) => p / sum
  );

  const random = Math.random();
  let cumulative = 0;
  for (let i = 0; i < question_probablilities.length; i++) {
    cumulative += question_probablilities[i];
    if (random < cumulative) {
      return i;
    }
  }
}

server.listen(8080, () => {
  console.log("Server is listening on port 8080");
});
