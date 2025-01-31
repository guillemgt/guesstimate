import { query } from "express";
import fs from "fs";
import http from "http";
import { WebSocketServer } from "ws";
import url from "url";

class Room {
  constructor() {
    this.players = new Map(); // uuid -> ws
    this.currentQuestion = null;
    this.totalScores = new Map(); // uuid -> score
    this.answersThisRound = new Map(); // uuid -> answer
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
  ws.uuid = query.uuid;
  ws.on("message", (message) => {
    try {
      const data = JSON.parse(message);

      switch (data.action) {
        case "create_room": {
          const roomCode = generateRoomCode();
          const room = new Room();
          room.players.set(ws.uuid, ws);
          rooms.set(roomCode, room);
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
          } else {
            ws.send(
              JSON.stringify({ action: "error", message: "Room not found." })
            );
          }
          break;
        }

        case "start_round": {
          const roomCode = ws.roomCode;
          const room = rooms.get(roomCode);
          if (!room) return;

          const questionIndex = Math.floor(
            Math.random() * ALL_QUESTIONS.length
          );
          const question = ALL_QUESTIONS[questionIndex];
          room.currentQuestion = { question, index: questionIndex };
          room.answersThisRound = new Map();

          broadcast(roomCode, { action: "new_question", question });
          break;
        }

        case "submit_answer": {
          const { answer } = data;
          const roomCode = ws.roomCode;
          const room = rooms.get(roomCode);
          if (!room || !room.currentQuestion) return;

          room.answersThisRound.set(ws.uuid, answer);

          if (room.answersThisRound.size === room.players.size) {
            const question = room.currentQuestion.question;
            const player_answers = room.answersThisRound;
            const player_scores = computeScores(player_answers, question);
            const player_answers_and_scores = Array.from(player_answers).map(
              ([player_uuid, answer]) => ({
                player: room.players.get(player_uuid).playerName,
                answer,
                score: player_scores.get(player_uuid),
              })
            );

            room.players.forEach((player) => {
              const score = player_scores.get(player);
              room.totalScores.set(
                player,
                room.totalScores.get(player) + score
              );
            });

            broadcast(roomCode, {
              action: "round_scores",
              data: player_answers_and_scores,
              correct_answer: question.answer,
              excerpt: question.excerpt,
            });
            room.currentQuestion = null;
          } else {
            ws.send(JSON.stringify({ action: "answer_submitted" }));
          }
          break;
        }

        case "vote_question": {
          const { vote } = data; // "good" or "bad"
          const roomCode = ws.roomCode;
          const room = rooms.get(roomCode);
          if (!room || !room.currentQuestion) return;

          const questionIndex = room.currentQuestion.index;
          if (vote === "good") GLOBAL_VOTES[questionIndex].good++;
          if (vote === "bad") GLOBAL_VOTES[questionIndex].bad++;

          break;
        }

        default:
          ws.send(
            JSON.stringify({ action: "error", message: "Unknown action." })
          );
      }
    } catch (err) {
      console.log(err);
      ws.send(
        JSON.stringify({ action: "error", message: "Invalid message format." })
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
