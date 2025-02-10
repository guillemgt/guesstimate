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
    console.log(this.totalScores);

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

function scale_independet_difference(a, b) {
  return (50.0 * (a - b)) / (40.0 + Math.abs(a));
}

function computeScores(player_answer, question) {
  const scores = new Map();
  const L = question["scale-interval"]["lower_bound"];
  const U = question["scale-interval"]["upper_bound"];
  player_answer.forEach((answer, player) => {
    const correct = question.answer;

    let score = 0;
    if (L !== null) {
      if (U === null) {
        // For bounded-below questions, use a logarithmic penalty (scaled by the log of the answer)
        const log_correct = Math.log(correct - L);
        const log_answer = Math.log(answer - L);
        const diff = scale_independet_difference(log_correct, log_answer);
        const diff_sigmoid = 1 / (1 + Math.exp(-diff));
        score = Math.max(0, 1 - Math.abs(1.0 - 2.0 * diff_sigmoid));
        // console.log("log_correct", log_correct);
        // console.log("log_answer", log_answer);
        // console.log("diff", diff);
        // console.log("diff_sigmoid", diff_sigmoid);
        // console.log("score", score);
      } else {
        const correct_normalized = (correct - L) / (U - L);
        const answer_normalized = (answer - L) / (U - L);

        // If bounded on both sides, use a penalty that is approximately logarithmic if the answer is near the edges but approximately linear if not
        const correct_logit = Math.log(
          correct_normalized / (1 - correct_normalized)
        );
        const answer_logit = Math.log(
          answer_normalized / (1 - answer_normalized)
        );
        const diff = scale_independet_difference(correct_logit, answer_logit);
        const diff_sigmoid = 1 / (1 + Math.exp(-diff));
        score = Math.max(0, 1 - Math.abs(1.0 - 2.0 * diff_sigmoid));

        // console.log("correct_normalized", correct_normalized);
        // console.log("answer_normalized", answer_normalized);
        // console.log("correct_logit", correct_logit);
        // console.log("answer_logit", answer_logit);
        // console.log("diff", diff);
        // console.log("diff_sigmoid", diff_sigmoid);
        // console.log("score", score);
      }
    }
    scores.set(player, parseInt(1000 * score));
  });
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
