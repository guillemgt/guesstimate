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
    const questionIndex = Math.floor(Math.random() * ALL_QUESTIONS.length);
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

    this.players.forEach((player) => {
      const score = player_scores.get(player);
      this.totalScores.set(player, this.totalScores.get(player) + score);
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
const GLOBAL_VOTES = ALL_QUESTIONS.map(() => ({ good: 0, bad: 0 }));

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
      room.players.delete(ws);
      room.answersThisRound.delete(ws);

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

function computeScores(player_answer, question) {
  const scores = new Map();
  player_answer.forEach((answer, player) => {
    const correct = question.correct_answer;
    const score = answer === correct ? 1 : 0;
    scores.set(player, score);
  });
  return scores;
}

server.listen(8080, () => {
  console.log("Server is listening on port 8080");
});
