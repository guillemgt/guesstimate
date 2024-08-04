
import path from 'path';
import fs from 'fs';


/* =============================
    Calling APIs
   ============================= */

import { do_openai_requests, compute_price } from "./general/openai.js"
import { wrap_prompt, filter_questions } from "./general/utils.js"


/* =============================
    Main
   ============================= */

async function main(params = {
    "input_path": "data/find_excerpt.json",
    "output_path": "data/filter_clear.json",
    "log_path": "data/logs/filter_clear/",
    "system_prompt_path": "prompts/filter_clear_system.txt",
    "examples_prompt_path": "prompts/filter_clear_examples.json",
    "temperature": 1.0,
    "num_votes": 5,
}) {
    const questions = JSON.parse(fs.readFileSync(params.input_path));

    // Form the prompts
    const system_prompt = fs.readFileSync(params.system_prompt_path, 'utf8');
    const prompt_examples = JSON.parse(fs.readFileSync(params.examples_prompt_path, 'utf8'));

    let prompts = [];
    for(let question of questions){

        let prompt = await wrap_prompt(question.description, system_prompt, prompt_examples, {examples_as_messages: false});

        prompts.push(prompt);
    }
    
    fs.mkdirSync(params.log_path, { recursive: true });
    
    const batch_call_id = "filter_clear";
    let [outputs, input_usage, output_usage] = await do_openai_requests(
        prompts,
        batch_call_id,
        params.log_path,
        {
            force_json: false,
            use_batch_api: true,
            temperature: params.temperature,
            num_choices: params.num_votes,
            max_tokens: 256
        }
    );
    console.log(input_usage, "IT,", output_usage, "OT,", compute_price(input_usage, output_usage) + "$");
    
    let new_questions = await filter_questions(questions, outputs, path.join(params.log_path, "evaluations.json"));

    console.log("Filtered to", new_questions.length)

    fs.writeFileSync(params.output_path, JSON.stringify(new_questions));
}

export { main };

// GPT-4o mini: $2.4159 for 10797 -> 3842 questions