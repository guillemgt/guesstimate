# Guesstimate

A pipeline to generate questions about estimating unknown quantities with AI.

You can play the game [here](https://tarr.ch/guesstimate).

## Usage

### Generating the questions

With GPT-4o, generating 3,500+ questions (out of 1,000+ topics and 10,000+ initial questions) cost $5.355 (an average of 6+ questions per cent).

Before you use it, modify the topics in `topics.json` if necessary.

Create a file called `.env` containing ```OPENAI_API_KEY=<your OpenAI key>```.

Run with `node generate-questions.js`.

### Web interface

Move the generated `data.json.gz` to the `interface/` directory and start a web server in that folder.
