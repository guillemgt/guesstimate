# Guesstimate

A pipeline to generate questions about estimating unknown quantities with AI.

You can play the game [here](https://tarr.ch/guesstimate).

## Usage

### Generating the questions

With the current pipeline (with GPT-4o-mini and GPT-4o), generating 3,000 questions (filtered out of 50,000+ initial questions) costs approximately $20.

Create a file called `.env` containing `OPENAI_API_KEY=<your OpenAI key>`.

To run the pipeline: `python src/main.py`.

### Web interface

Move the generated file to to `interface/backend/data.json` directory and execute `server.js` with `node`. Finally, start a webserver in `interface/frontend`.
