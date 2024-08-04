import path from 'path';
import { config } from 'dotenv';
config();

import fs from 'fs';



/* =============================
    Number parser
   ============================= */


import { printNumberOrIntervalWithUnits } from "./general/numbers.js"


/* =============================
    Calling APIs
   ============================= */

import { do_openai_requests, compute_price } from "./general/openai.js"
import { wrap_prompt, filter_questions, get_description } from "./general/utils.js"


/* =============================
    Main
   ============================= */

async function main(params = {
    "input_path": "data/rewrite_description.json",
    "output_path": "data/filter_correct.json",
    "log_path": "/data/logs/filter_correct/",
    "system_prompt_path": "prompts/filter_correct_system.txt",
    "examples_prompt_path": "prompts/filter_correct_examples.json",
    "temperature": 1.0,
    "num_votes": 5
}) {
    const questions = JSON.parse(fs.readFileSync(params.input_path));

    // Form the prompts
    const system_prompt = fs.readFileSync(params.system_prompt_path, 'utf8');
    const prompt_examples = JSON.parse(fs.readFileSync(params.examples_prompt_path, 'utf8'));

    let prompts = [];
    for(let question of questions){

        let prompt = await wrap_prompt({
            "description": get_description(question),
            "answer": printNumberOrIntervalWithUnits(question.answer, question.unit, question.answer_is_approximate),
            "excerpt": question.found_excerpt,
        }, system_prompt, prompt_examples);

        prompts.push(prompt);
    }
    
    fs.mkdirSync(params.log_path, { recursive: true });
    
    const batch_call_id = "filter_correct";
    let [outputs, input_usage, output_usage] = await do_openai_requests(
        prompts,
        batch_call_id,
        params.log_path,
        {
            force_json: false,
            use_batch_api: true,
            temperature: params.temperature,
            num_choices: params.num_votes,
        }
    );
    console.log(input_usage, "IT,", output_usage, "OT,", compute_price(input_usage, output_usage) + "$");

    let new_questions = await filter_questions(questions, outputs, path.join(params.log_path, "evaluations.json"));

    console.log("Filtered to", new_questions.length)

    fs.writeFileSync(params.output_path, JSON.stringify(new_questions));
}

export { main };

// GPT-4o mini: $0.5285 for 3815 -> 3553 questions